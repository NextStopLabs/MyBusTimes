# core/context_processors.py

def memory_debug(request):
    return {
        "mem_debug": getattr(request, "_mem_debug", None)
    }