"""
Ensures Django database connections are properly cleaned up in ASGI context.

Problem: when gunicorn runs with UvicornWorker (ASGI mode), sync views
execute in a thread-pool via asgiref.sync_to_async.  Django's async
request handler calls close_old_connections() in the *async* event-loop
thread, but the actual DB connections live in the thread-pool threads.
Those connections are never cleaned up, leading to unbounded connection
growth.
"""

import os
from concurrent.futures import ThreadPoolExecutor

from asgiref.sync import SyncToAsync
from django.db import close_old_connections

def _get_thread_pool_size():
    raw = os.getenv("DB_THREAD_POOL_SIZE", "4")
    try:
        val = int(raw)
    except (TypeError, ValueError):
        val = 4
    # Clamp to at least 1 – Coolify UI may set empty/0 which would raise ValueError in ThreadPoolExecutor
    return max(1, val)


_DB_THREAD_POOL_SIZE = _get_thread_pool_size()

# Bounded shared pool used when sync_to_async is called with
# thread_sensitive=False and no explicit executor.
_shared_executor = ThreadPoolExecutor(
    max_workers=_DB_THREAD_POOL_SIZE,
    thread_name_prefix="mbt-db",
)

# ---------------------------------------------------------------------------
# 1. Patch thread_handler so every thread-pool thread closes its DB
#    connection in a finally block, regardless of which executor was used.
#    This is the most direct fix - the thread that opened the connection
#    is responsible for cleaning it up.
# ---------------------------------------------------------------------------
_orig_thread_handler = SyncToAsync.thread_handler


def _patched_thread_handler(self, loop, exc_info, task_context, func, *args, **kwargs):
    try:
        return _orig_thread_handler(self, loop, exc_info, task_context, func, *args, **kwargs)
    finally:
        try:
            close_old_connections()
        except Exception:
            pass


SyncToAsync.thread_handler = _patched_thread_handler

# ---------------------------------------------------------------------------
# 2. Patch __call__ to route thread_sensitive=False calls that would use
#    loop's unbounded default executor through our bounded shared pool.
#    Without this, each request could create ephemeral threads.
# ---------------------------------------------------------------------------
_orig_call = SyncToAsync.__call__


async def _call_with_bounded_executor(self, *args, **kwargs):
    # Only intervene for non-sensitive code that didn't supply an executor.
    # thread_sensitive=True must use its dedicated single_thread_executor.
    should_override = False
    if not getattr(self, "_thread_sensitive", True):
        if getattr(self, "_executor", None) is None:
            should_override = True
            self._executor = _shared_executor
    try:
        return await _orig_call(self, *args, **kwargs)
    finally:
        if should_override:
            self._executor = None


SyncToAsync.__call__ = _call_with_bounded_executor


def install_db_connection_management():
    """
    Kept for backwards compatibility – called from mybustimes.asgi:application
    after django.setup(). Shared executor is already created at import; this
    just exposes it on the running loop for introspection and optionally sets
    it as the loop's default executor.
    """
    try:
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop._mbt_db_executor = _shared_executor
        try:
            loop.set_default_executor(_shared_executor)
        except Exception:
            pass
    except Exception:
        pass
