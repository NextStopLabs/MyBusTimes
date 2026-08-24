"""
Ensures Django database connections are properly cleaned up in ASGI context.

Problem: when gunicorn runs with UvicornWorker (ASGI mode), sync views
execute in a thread-pool via asgiref.sync_to_async.  Django's async
request handler calls close_old_connections() in the *async* event-loop
thread, but the actual DB connections live in the thread-pool threads.
Those connections are never cleaned up, leading to unbounded connection
growth.

Fix: wrap the sync function so close_old_connections() runs *inside* the
thread-pool thread that owns the connection (try/finally). Also provide
a bounded shared executor so sync_to_async doesn't create unbounded
ephemeral threads, each pinning a DB connection.
"""

import functools
import os
from concurrent.futures import ThreadPoolExecutor

from asgiref.sync import SyncToAsync
from django.db import close_old_connections

_DB_THREAD_POOL_SIZE = int(os.getenv("DB_THREAD_POOL_SIZE", "4"))

# Bounded shared pool used when sync_to_async is called without an explicit
# executor.  Eagerly created at import time so it exists before any event
# loop is running (fixes previous no-op install_db_connection_management).
_shared_executor = ThreadPoolExecutor(
    max_workers=_DB_THREAD_POOL_SIZE,
    thread_name_prefix="mbt-db",
)

_orig_call = SyncToAsync.__call__


async def _call_with_cleanup(self, *args, **kwargs):
    """
    Patch SyncToAsync.__call__ so every thread-pool thread cleans up its
    DB connection immediately after the sync work completes.

    Previous version did `if self.executor is not None: run_in_executor(executor, close_old_connections)`
    which missed the common case where executor is None (default pool) and
    ran cleanup in a *second* dispatch rather than in the owning thread.
    """
    # Wrap the user function so close_old_connections runs in the SAME
    # thread that opened the connection, regardless of which executor is used.
    original_func = self.func

    @functools.wraps(original_func)
    def _wrapped(*a, **kw):
        try:
            return original_func(*a, **kw)
        finally:
            try:
                close_old_connections()
            except Exception:
                pass

    # Temporarily replace func for the duration of the call.
    self.func = _wrapped
    # If no explicit executor was supplied, route through the bounded shared pool
    # instead of the loop's default unbounded pool.
    executor_overridden = False
    original_executor = self.executor
    if original_executor is None:
        self.executor = _shared_executor
        executor_overridden = True
    try:
        return await _orig_call(self, *args, **kwargs)
    finally:
        self.func = original_func
        if executor_overridden:
            self.executor = original_executor


SyncToAsync.__call__ = _call_with_cleanup


def install_db_connection_management():
    """
    Kept for backwards compatibility – called from mybustimes.asgi:application
    after django.setup().  Previously this tried to create an executor tied to
    the running loop (which didn't exist yet at import time). Now the shared
    executor is already created at import; this just ensures any already-running
    loop uses it as default executor if possible.

    Safe to call multiple times and from any thread.
    """
    try:
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        # Expose for introspection; also set as loop default executor so
        # any other sync_to_async without executor reuses the bounded pool.
        loop._mbt_db_executor = _shared_executor
        try:
            loop.set_default_executor(_shared_executor)
        except Exception:
            pass
    except Exception:
        pass
