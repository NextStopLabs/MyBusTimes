from django.shortcuts import render
from words.models import bannedWord, whitelistedWord
from main.models import BannedIps
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import re

def ban_ip(self, request):
    """Return the real client IP, even behind proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # X-Forwarded-For may contain multiple IPs — first is the real client
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    
    BannedIps.objects.get_or_create(
        ip_address=ip,
        banned_at=timezone.now(),
        related_user=request.user if request.user.is_authenticated else None,
        reason='Used banned word in text scan'
    )

@csrf_exempt
def check_string_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=400)

    query = request.POST.get('query', '').strip()
    if not query:
        return JsonResponse({'error': 'No query provided'}, status=400)

    words = [w for w in re.split(r'\s+', query) if w]

    # Load word lists once for efficiency
    banned_set = set(b.lower() for b in bannedWord.objects.values_list('word', flat=True))
    whitelisted_set = set(w.lower() for w in whitelistedWord.objects.values_list('word', flat=True))

    results = []
    insta_banned = False

    for w in words:
        lw = w.lower()

        if lw in whitelisted_set:
            status = 'ok'
        elif lw in banned_set:
            status = 'banned'
            # Check if it's an insta-ban word
            if bannedWord.objects.filter(word__iexact=lw, insta_ban=True).exists():
                status = 'banned'
                insta_banned = True
        else:
            status = 'ok'

        results.append({'word': w, 'status': status})

    # Handle user banning (if authenticated)
    if insta_banned and request.user.is_authenticated:
        ban_ip(request, request)
        user = request.user
        user.banned = True
        user.banned_reason = f'Used banned word in text: "{query}"'
        user.banned_date = "9999-12-31 23:59:59"
        user.save(update_fields=['banned', 'banned_reason', 'banned_date'])


    return JsonResponse({
        'query': query,
        'results': results,
        'insta_banned': insta_banned,
    })
