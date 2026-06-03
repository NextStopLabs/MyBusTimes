# core/context_processors.py

def memory_debug(request):
    print("Memory Debug Context Processor called")
    return {
        "mem_debug": getattr(request, "_mem_debug", None)
    }