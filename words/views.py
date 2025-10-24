from django.shortcuts import render
from words.models import bannedWord, whitelistedWord
import re
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def check_string_view(request):
    query = ''
    results = None

    if request.method == 'POST':
        query = request.POST.get('query', '').strip()
        words = [w for w in re.split(r'\s+', query) if w]

        # load lists once for efficiency (case-insensitive)
        banned_set = set(b.lower() for b in bannedWord.objects.values_list('word', flat=True))
        whitelisted_set = set(w.lower() for w in whitelistedWord.objects.values_list('word', flat=True))

        results = []
        for w in words:
            lw = w.lower()
            if lw in whitelisted_set:
                status = 'ok'
            elif lw in banned_set:
                status = 'banned'
            else:
                status = 'ok'
            results.append({'word': w, 'status': status})

    return JsonResponse({
        'query': query,
        'results': results,
    })