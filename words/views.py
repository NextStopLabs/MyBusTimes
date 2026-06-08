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
from main.cloudflare_ips import get_cloudflare_networks, is_cloudflare_ip

discord_id = 1432696791735734333
DEFAULT_BANNED_WORD_SCOPE = bannedWord.SEARCH_SCOPE

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

    if not settings.DISABLE_JESS:
        response = requests.post(
            f"{settings.DISCORD_BOT_API_URL}/send-embed",
            json=data
        )
        response.raise_for_status()

def get_real_ip(request):
    ip = request.META.get('HTTP_CF_CONNECTING_IP')
    if ip:
        return ip.strip()

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()

    return request.META.get('REMOTE_ADDR', '').strip()

def ban_ip(self, request, banned_word):
    ip = get_real_ip(request)

    # Make sure we actually *have* an IP
    if not ip:
        return

    # Never ban Cloudflare IPs (this would ban everyone)
    if is_cloudflare_ip(ip):
        send_to_discord_embed(
            discord_id,
            "⚠️ Ban Prevented",
            f"Attempted ban on Cloudflare IP `{ip}` was blocked for safety."
        )
        return

    # Create or update ban entry
    ban, created = BannedIps.objects.get_or_create(
        ip_address=ip,
        defaults={
            "banned_at": timezone.now(),
            "related_user": request.user if request.user.is_authenticated else None,
            "reason": f'Used banned word "{banned_word}" in text scan'
        }
    )

    # Log to Discord
    send_to_discord_embed(
        discord_id,
        "IP Banned",
        f"The IP `{ip}` has been banned for saying banned word `{banned_word}`."
    )

    return ban  # Optional: can return the model instance

@csrf_exempt
def check_string_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=400)

    query = request.POST.get('query', '').strip()
    if not query:
        return JsonResponse({'error': 'No query provided'}, status=400)

    scope = request.POST.get('scope', DEFAULT_BANNED_WORD_SCOPE).strip() or DEFAULT_BANNED_WORD_SCOPE
    if scope != 'all' and not bannedWord.valid_scope(scope):
        return JsonResponse({
            'error': 'Invalid scope provided',
            'valid_scopes': ['all', *bannedWord.SCOPE_FIELD_MAP.keys()],
        }, status=400)

    words = [w for w in re.split(r'\s+', query) if w]

    # Load word lists once for efficiency
    banned_words = bannedWord.objects.all()
    if scope != 'all':
        banned_words = banned_words.filter(**{bannedWord.SCOPE_FIELD_MAP[scope]: True})

    banned_set = set(b.lower() for b in banned_words.values_list('word', flat=True))
    whitelisted_set = set(w.lower() for w in whitelistedWord.objects.values_list('word', flat=True))
    insta_ban_set = set(b.lower() for b in banned_words.filter(insta_ban=True).values_list('word', flat=True))

    results = []
    insta_banned = False

    word = ''

    for w in words:
        lw = w.lower()

        if lw in whitelisted_set:
            status = 'ok'
        elif lw in banned_set:
            status = 'banned'
            if lw in insta_ban_set:
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
        'scope': scope,
        'results': results,
        'insta_banned': insta_banned,
    })
