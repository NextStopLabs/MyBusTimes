import ipaddress
import logging
import queue
import re
import threading

import requests
from django.conf import settings
from django.core.cache import cache
from django.db import close_old_connections
from django.utils import timezone

from .models import CustomUser, SuspiciousSignupAlert


logger = logging.getLogger(__name__)

DISPOSABLE_EMAIL_DOMAINS = {
    '10minutemail.com',
    'dispostable.com',
    'guerrillamail.com',
    'mailinator.com',
    'sharklasers.com',
    'tempmail.com',
    'trashmail.com',
    'yopmail.com',
}

SUSPICIOUS_USERNAME_PATTERNS = (
    re.compile(r'(alt|test|temp|throwaway|spam|bot)', re.IGNORECASE),
    re.compile(r'\d{4,}'),
)

SUSPICIOUS_USERNAME_LENGTH_THRESHOLD = 4
SUSPICIOUS_ALERT_THRESHOLD = 5
SUSPICIOUS_VPN_ALERT_SCORE = 6

_FLAG_QUEUE = queue.Queue()
_WORKER_LOCK = threading.Lock()
_WORKER_THREAD = None


def enqueue_signup_flagging(user_id):
    start_flagging_worker()
    _FLAG_QUEUE.put(user_id)


def start_flagging_worker():
    global _WORKER_THREAD

    with _WORKER_LOCK:
        if _WORKER_THREAD and _WORKER_THREAD.is_alive():
            return

        _WORKER_THREAD = threading.Thread(target=_worker_loop, daemon=True)
        _WORKER_THREAD.start()


def _worker_loop():
    while True:
        user_id = _FLAG_QUEUE.get()
        try:
            close_old_connections()
            process_signup_flag(user_id)
        except Exception:
            logger.exception('Unexpected error while processing suspicious signup flag for user %s', user_id)
        finally:
            close_old_connections()
            _FLAG_QUEUE.task_done()


def process_signup_flag(user_id):
    user = CustomUser.objects.filter(pk=user_id).first()
    if user is None or user.is_staff or user.is_superuser:
        return

    score, reasons, matching_ips, matching_usernames = assess_user_suspicion(user)
    if score < SUSPICIOUS_ALERT_THRESHOLD:
        return

    alert, _ = SuspiciousSignupAlert.objects.update_or_create(
        user=user,
        defaults={
            'score': score,
            'reasons': reasons,
            'matching_ips': matching_ips,
            'matching_usernames': matching_usernames,
        },
    )

    if send_suspicious_signup_webhook(alert):
        SuspiciousSignupAlert.objects.filter(pk=alert.pk).update(webhook_sent_at=timezone.now())


def assess_user_suspicion(user):
    score = 0
    reasons = []
    matching_ips = []
    matching_usernames = []

    username = (user.username or '').strip()
    email = (user.email or '').strip()

    ip_values = []
    for value in (getattr(user, 'last_ip', None), getattr(user, 'last_login_ip', None)):
        normalized = normalize_ip(value)
        if normalized and normalized not in ip_values:
            ip_values.append(normalized)

    if not email:
        score += 2
        reasons.append('No email address provided.')
    else:
        email_domain = email.rsplit('@', 1)[-1].lower() if '@' in email else ''
        if email_domain in DISPOSABLE_EMAIL_DOMAINS:
            score += 4
            reasons.append(f'Email domain looks disposable: {email_domain}.')

    if len(username) <= SUSPICIOUS_USERNAME_LENGTH_THRESHOLD:
        score += 1
        reasons.append('Username is very short.')

    if any(pattern.search(username) for pattern in SUSPICIOUS_USERNAME_PATTERNS):
        score += 2
        reasons.append('Username matches a suspicious pattern.')

    if ip_values:
        vpn_matches = []
        for ip_value in ip_values:
            vpn_reason = assess_vpn_or_proxy_ip(ip_value)
            if vpn_reason:
                score += SUSPICIOUS_VPN_ALERT_SCORE
                vpn_matches.append(f'{ip_value}: {vpn_reason}')

        if vpn_matches:
            reasons.extend(vpn_matches)

        shared_usernames = find_users_sharing_ips(user, ip_values)
        if shared_usernames:
            score += 5
            matching_ips.extend(ip_values)
            matching_usernames.extend(shared_usernames)
            reasons.append(
                f'IP shared with {len(shared_usernames)} other account(s): {", ".join(shared_usernames[:5])}.'
            )

    if score == 0:
        reasons.append('No suspicious signals detected.')

    return score, reasons, sorted(set(matching_ips)), sorted(set(matching_usernames))


def find_users_sharing_ips(user, ip_values):
    current_user_ids = set(
        CustomUser.objects.filter(last_ip__in=ip_values)
        .exclude(pk=user.pk)
        .values_list('pk', flat=True)
    )
    current_user_ids.update(
        CustomUser.objects.filter(last_login_ip__in=ip_values)
        .exclude(pk=user.pk)
        .values_list('pk', flat=True)
    )

    historical_model = CustomUser.history.model
    historical_user_ids = set(
        historical_model.objects.filter(last_ip__in=ip_values)
        .exclude(id=user.pk)
        .values_list('id', flat=True)
    )
    historical_user_ids.update(
        historical_model.objects.filter(last_login_ip__in=ip_values)
        .exclude(id=user.pk)
        .values_list('id', flat=True)
    )

    user_ids = sorted(current_user_ids | historical_user_ids)
    if not user_ids:
        return []

    return list(
        CustomUser.objects.filter(pk__in=user_ids).order_by('username').values_list('username', flat=True)
    )


def send_suspicious_signup_webhook(alert):
    webhook_url = getattr(settings, 'DISCORD_SUSPICIOUS_USER_WEBHOOK', None)
    if not webhook_url:
        logger.warning(
            'DISCORD_SUSPICIOUS_USER_WEBHOOK is not configured; skipping suspicious signup alert for user %s',
            alert.user_id,
        )
        return False

    content = (
        f'Suspicious signup flagged: {alert.user.username} (id={alert.user_id}) '
        f'score={alert.score}. '
        f'Reasons: {"; ".join(alert.reasons) or "none"}.'
    )

    embed = {
        'title': 'Suspicious signup flagged',
        'description': f'User {alert.user.username} was flagged by the signup monitor.',
        'color': 0xF59E0B,
        'fields': [
            {'name': 'User ID', 'value': str(alert.user_id), 'inline': True},
            {'name': 'Username', 'value': alert.user.username or '-', 'inline': True},
            {'name': 'Email', 'value': alert.user.email or '-', 'inline': False},
            {'name': 'Score', 'value': str(alert.score), 'inline': True},
            {'name': 'IPs', 'value': truncate_discord_field(', '.join(alert.matching_ips) or '-'), 'inline': False},
            {'name': 'Matching users', 'value': truncate_discord_field(', '.join(alert.matching_usernames) or '-'), 'inline': False},
            {
                'name': 'Reasons',
                'value': truncate_discord_field('\n'.join(f'- {reason}' for reason in alert.reasons) or '-'),
                'inline': False,
            },
        ],
        'footer': {'text': 'MyBusTimes suspicious signup monitor'},
        'timestamp': timezone.now().isoformat(),
    }

    try:
        response = requests.post(webhook_url, json={'content': content, 'embeds': [embed]}, timeout=5)
        response.raise_for_status()
        return True
    except Exception:
        logger.exception('Failed to send suspicious signup webhook for user %s', alert.user_id)
        return False


def assess_vpn_or_proxy_ip(ip_value):
    if not getattr(settings, 'VPN_DETECTION_API_KEY', None):
        return None

    api_url = getattr(settings, 'VPN_DETECTION_API_URL', '').rstrip('/')
    if not api_url:
        return None

    cache_key = f'vpn_check:{ip_value}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached or None

    try:
        response = requests.get(
            f'{api_url}/{ip_value}',
            params={
                'key': settings.VPN_DETECTION_API_KEY,
                'vpn': 1,
                'asn': 1,
                'risk': 1,
            },
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        logger.warning('VPN lookup failed for IP %s', ip_value)
        cache.set(cache_key, '', 300)
        return None

    ip_payload = payload.get(ip_value, {}) if isinstance(payload, dict) else {}
    if not isinstance(ip_payload, dict):
        cache.set(cache_key, '', 300)
        return None

    proxy_value = str(ip_payload.get('proxy', '')).lower()
    type_value = str(ip_payload.get('type', '')).upper()
    risk_value = ip_payload.get('risk')

    if proxy_value in {'yes', 'true', '1'} or type_value in {'VPN', 'PROXY', 'TOR'}:
        result = 'IP is flagged as a VPN/proxy/Tor endpoint.'
        cache.set(cache_key, result, 3600)
        return result

    try:
        if risk_value is not None and float(risk_value) >= 75:
            result = f'IP risk score is high ({risk_value}).'
            cache.set(cache_key, result, 3600)
            return result
    except (TypeError, ValueError):
        pass

    cache.set(cache_key, '', 3600)
    return None


def normalize_ip(value):
    if not value:
        return None

    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return None


def truncate_discord_field(value, limit=1024):
    if len(value) <= limit:
        return value

    return value[: limit - 3] + '...'