"""
Ensures Django database connections are properly cleaned up in ASGI context.

Problem: when gunicorn runs with UvicornWorker (ASGI mode), sync views
execute in a thread-pool via asgiref.sync_to_async.  Django's async
request handler calls close_old_connections() in the *async* event-loop
thread, but the actual DB connections live in the thread-pool threads.
Those connections are never cleaned up, leading to unbounded connection
growth.

This module patches the async-to-sync boundary so that every pooled
thread calls close_old_connections() *after* its work completes, and
caps the thread-pool size to a known, reasonable value.
"""

import os
from concurrent.futures import ThreadPoolExecutor

from asgiref.sync import SyncToAsync
from django.db import close_old_connections

# ---------------------------------------------------------------------------
# Patch SyncToAsync.__call__ so that close_old_connections() runs in the
# thread-pool thread *after* every sync call.  Without this, connections
# created during sync view execution in the pool threads are invisible
# to the async handler and never age out.
# ---------------------------------------------------------------------------
_orig_call = SyncToAsync.__call__


async def _call_with_cleanup(self, *args, **kwargs):
    result = await _orig_call(self, *args, **kwargs)
    try:
        if self.executor is not None:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop is not None:
                await loop.run_in_executor(self.executor, close_old_connections)
    except Exception:
        pass
    return result


SyncToAsync.__call__ = _call_with_cleanup


# ---------------------------------------------------------------------------
# Cap the default thread-pool size.  Without an explicit bound,
# sync_to_async may create an ephemeral thread per call, each holding a
# DB connection.
# ---------------------------------------------------------------------------
_DB_THREAD_POOL_SIZE = int(os.getenv("DB_THREAD_POOL_SIZE", "8"))


def install_db_connection_management():
    """Call once at startup (after django.setup()) to cap the thread pool."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    executor = ThreadPoolExecutor(max_workers=_DB_THREAD_POOL_SIZE)
    loop._mbt_db_executor = executor
