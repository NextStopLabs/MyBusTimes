# core/middleware/perf_debug.py

import time
import os
import psutil
from django.db import connection, reset_queries
from collections import Counter

process = psutil.Process(os.getpid())


class MemoryDebugMiddleware:
    """
    Advanced performance + DB debugging middleware.

    Tracks:
    - Memory usage (RSS)
    - Request duration
    - DB query count
    - Total DB time
    - Slow queries
    - Duplicate queries (ORM inefficiencies)
    """

    SLOW_QUERY_THRESHOLD = 0.05  # seconds (50ms)
    MAX_QUERIES_TO_PRINT = 5
    API_SKIP_PREFIXES = ('/api/',)

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(self.API_SKIP_PREFIXES):
            return self.get_response(request)

        # --- START METRICS ---
        reset_queries()

        start_mem = process.memory_info().rss / 1024 / 1024
        start_time = time.time()

        # --- REQUEST ---
        response = self.get_response(request)

        # --- END METRICS ---
        end_time = time.time()
        end_mem = process.memory_info().rss / 1024 / 1024

        duration = end_time - start_time
        mem_diff = end_mem - start_mem

        queries = connection.queries
        query_count = len(queries)

        total_db_time = sum(float(q.get("time", 0)) for q in queries)

        # --- FIND SLOW QUERIES ---
        slow_queries = [
            q for q in queries if float(q.get("time", 0)) >= self.SLOW_QUERY_THRESHOLD
        ]
        slow_queries_sorted = sorted(
            slow_queries,
            key=lambda q: float(q.get("time", 0)),
            reverse=True
        )

        # --- FIND DUPLICATE QUERIES ---
        query_sqls = [q["sql"] for q in queries]
        duplicates = Counter(query_sqls)
        repeated_queries = [q for q, count in duplicates.items() if count > 5]

        # --- HEADERS (lightweight insight in browser/devtools) ---
        response["X-Mem-Start"] = f"{start_mem:.1f}"
        response["X-Mem-End"] = f"{end_mem:.1f}"
        response["X-Mem-Diff"] = f"{mem_diff:.1f}"
        response["X-Req-Time"] = f"{duration:.2f}"
        response["X-DB-Queries"] = str(query_count)
        response["X-DB-Time"] = f"{total_db_time:.3f}"

        # --- LOG SUMMARY ---
        print(
            f"\n[PERF] {request.method} {request.path}\n"
            f"  Time: {duration:.2f}s | "
            f"Mem: {start_mem:.1f}MB → {end_mem:.1f}MB ({mem_diff:+.1f}MB)\n"
            f"  DB: {query_count} queries | {total_db_time:.3f}s\n"
        )

        # --- LOG SLOW QUERIES ---
        if slow_queries_sorted:
            print(f"  🐢 Slow Queries (>{self.SLOW_QUERY_THRESHOLD}s):")
            for q in slow_queries_sorted[:self.MAX_QUERIES_TO_PRINT]:
                print(f"    {q['time']}s | {q['sql'][:200]}...\n")

        # --- LOG DUPLICATES ---
        if repeated_queries:
            print(f"  🔁 Repeated Queries (>5x):")
            for q in repeated_queries[:self.MAX_QUERIES_TO_PRINT]:
                print(f"    {duplicates[q]}x | {q[:200]}...\n")

        # --- WARNING SIGNALS ---
        if query_count > 100:
            print("  ⚠️ HIGH QUERY COUNT (likely N+1 issue)")

        if total_db_time > 1.0:
            print("  ⚠️ DB TIME OVER 1s (slow queries or missing indexes)")

        if mem_diff > 50:
            print("  ⚠️ MEMORY SPIKE (>50MB)")

        print("-" * 80)

        return response