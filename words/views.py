from django.shortcuts import render
from words.models import bannedWord, whitelistedWord
from main.models import BannedIps
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import re
import requests
from django.conf import settings
from datetime import datetime

discord_id = 1432696791735734333

def send_to_discord_embed(discord_id, title, message, colour=0xED4245):
    embed = {
        "title": title,
        "description": message,
        "color": colour,
        "fields": [
            {
                "name": "Time",
                "value": datetime.now().strftime('%Y-%m-%d %H:%M'),
                "inline": True
            }
        ],
        "footer": {
            "text": "MBT Logging System"
        },
        "timestamp": datetime.now().isoformat()
    }

    data = {
        'channel_id': discord_id,
        'embed': embed
    }

    response = requests.post(
        f"{settings.DISCORD_BOT_API_URL}/send-embed",
        json=data
    )
    response.raise_for_status()

def ban_ip(self, request, banned_word):
    """Return the real client IP, even behind proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # X-Forwarded-For may contain multiple IPs — first is the real client
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')

    send_to_discord_embed(
        discord_id,
        "IP Banned",
        f"The IP address {ip} has been banned for using the word {banned_word} in text scan."
    )
    
    BannedIps.objects.get_or_create(
        ip_address=ip,
        banned_at=timezone.now(),
        reason=f'Used banned word "{banned_word}" in text scan'
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

    word = ''

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
        ban_ip(request, request, query)
        user = request.user
        user.banned = True
        user.banned_reason = f'Used banned word in text: "{query}"'
        user.banned_date = "9999-12-31 23:59:59"
        user.save(update_fields=['banned', 'banned_reason', 'banned_date'])
    elif insta_banned:
        ban_ip(request, request, query)


    return JsonResponse({
        'query': query,
        'results': results,
        'insta_banned': insta_banned,
    })
