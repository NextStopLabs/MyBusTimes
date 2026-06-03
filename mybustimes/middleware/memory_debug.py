# core/middleware/memory_debug.py

import psutil
import os
import time

process = psutil.Process(os.getpid())

class MemoryDebugMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_mem = process.memory_info().rss / 1024 / 1024
        start_time = time.time()

        response = self.get_response(request)

        end_mem = process.memory_info().rss / 1024 / 1024
        duration = time.time() - start_time

        mem_data = {
            "start": round(start_mem, 1),
            "end": round(end_mem, 1),
            "diff": round(end_mem - start_mem, 1),
            "time": round(duration, 2),
            "path": request.path,
        }

        # ✅ attach to response headers instead
        response["X-Mem-Start"] = str(mem_data["start"])
        response["X-Mem-End"] = str(mem_data["end"])
        response["X-Mem-Diff"] = str(mem_data["diff"])
        response["X-Mem-Time"] = str(mem_data["time"])

        print(
            f"[MEM] {request.path} | "
            f"{start_mem:.1f}MB → {end_mem:.1f}MB "
            f"(+{end_mem - start_mem:.1f}MB) | "
            f"{duration:.2f}s"
        )

        return response