"""
Diagnostic middleware that logs per-request database connection and query
activity.  Helps identify endpoints that create excessive connections.

Activate by setting DB_DIAGNOSTICS_ENABLED=True in the environment.
"""

import logging
import os
import time
from collections import defaultdict
from threading import Lock

from django.db import connection, reset_queries

logger = logging.getLogger("db_diagnostics")

_ENABLED = os.getenv("DB_DIAGNOSTICS_ENABLED", "").lower() in ("true", "1", "yes")
_SAMPLE_RATE = float(os.getenv("DB_DIAGNOSTICS_SAMPLE_RATE", "0.01"))
_LOG_THRESHOLD_QUERIES = int(os.getenv("DB_DIAGNOSTICS_QUERY_THRESHOLD", "20"))

_endpoint_stats = defaultdict(lambda: {"hits": 0, "total_queries": 0})
_stats_lock = Lock()


def _get_view_name(request):
    resolver_match = getattr(request, "resolver_match", None)
    if resolver_match:
        return f"{resolver_match.view_name}"
    return request.path


class DatabaseDiagnosticsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not _ENABLED:
            return self.get_response(request)

        if _SAMPLE_RATE < 1.0 and hash(request.path) % 10000 > _SAMPLE_RATE * 10000:
            return self.get_response(request)

        # snapshot the connection identity before the request
        conn_before = id(connection.connection) if connection.connection else None
        t0 = time.perf_counter()
        reset_queries()

        response = self.get_response(request)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        query_count = len(connection.queries) if hasattr(connection, "queries") else 0
        conn_after = id(connection.connection) if connection.connection else None
        conn_reused = conn_before is not None and conn_before == conn_after
        conn_created = conn_before is None and conn_after is not None

        view_name = _get_view_name(request)

        logger.info(
            "[DB] view=%s queries=%d time_ms=%.1f conn_reused=%s conn_created=%s",
            view_name,
            query_count,
            elapsed_ms,
            conn_reused,
            conn_created,
        )

        if query_count >= _LOG_THRESHOLD_QUERIES:
            logger.warning("[DB] HIGH_QUERY_COUNT view=%s queries=%d", view_name, query_count)

        with _stats_lock:
            stats = _endpoint_stats[view_name]
            stats["hits"] += 1
            stats["total_queries"] += query_count

        return response


def log_endpoint_summary():
    """Print a summary of endpoint DB usage.  Call periodically or via management command."""
    with _stats_lock:
        if not _endpoint_stats:
            return
        entries = sorted(_endpoint_stats.items(), key=lambda x: x[1]["hits"], reverse=True)[:20]
    logger.info("[DB_SUMMARY] top endpoints by hit count:")
    for view, stats in entries:
        logger.info("[DB_SUMMARY]   %s  hits=%d  total_queries=%d", view, stats["hits"], stats["total_queries"])
