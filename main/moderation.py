import hashlib
import ipaddress
import uuid
from dataclasses import dataclass

from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from main.cloudflare_ips import get_cloudflare_networks
from main.models import BannedIps, Device, DeviceBan, DeviceUsage


DEVICE_COOKIE_NAME = "mbt_device_fp"
DEVICE_CACHE_TIMEOUT = 300
IP_CACHE_TIMEOUT = 300
USER_BAN_CACHE_TIMEOUT = 60
DEVICE_ACTIVITY_TIMEOUT = 600
LOCAL_IPS = {"127.0.0.1", "::1"}


@dataclass(frozen=True)
class DeviceBanResult:
    banned: bool = False
    reason: str | None = None
    fingerprint: str | None = None


def cache_delete_many(keys):
    try:
        cache.delete_many(keys)
    except AttributeError:
        for key in keys:
            cache.delete(key)


def is_cloudflare_ip(ip):
    if not ip:
        return False

    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        return False

    ipv4_nets, ipv6_nets = get_cloudflare_networks()
    nets = ipv4_nets if ip_obj.version == 4 else ipv6_nets
    return any(ip_obj in net for net in nets)


def get_real_ip(request):
    ip = request.META.get("HTTP_CF_CONNECTING_IP")
    if ip:
        return ip.strip()

    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR", "").strip()


def get_storage_ip(request):
    ip = get_real_ip(request)
    if not ip or ip in LOCAL_IPS or is_cloudflare_ip(ip):
        return None
    return ip


def get_device_fingerprint(request):
    fp = request.META.get("HTTP_X_DEVICE_FINGERPRINT")
    if fp:
        fp = fp.strip()[:64]
        if fp:
            return fp, False

    cookie_fp = request.COOKIES.get(DEVICE_COOKIE_NAME)
    if cookie_fp:
        cookie_fp = cookie_fp.strip()[:64]
        if cookie_fp:
            return cookie_fp, False

    new_fp = uuid.uuid4().hex
    request._generated_device_fp = new_fp
    return new_fp, True


def derive_device_fingerprint(request):
    parts = []
    for header in (
        "HTTP_USER_AGENT",
        "HTTP_ACCEPT_LANGUAGE",
        "HTTP_ACCEPT",
        "HTTP_SEC_CH_UA",
        "HTTP_SEC_CH_UA_MOBILE",
    ):
        value = request.META.get(header, "")
        if value:
            parts.append(value)

    if not parts:
        return None

    data = "|".join(parts).encode("utf-8")
    return "derived-" + hashlib.sha256(data).hexdigest()


def device_ban_cache_key(fingerprint):
    return f"moderation:device-ban:{fingerprint}"


def ip_ban_cache_key(ip):
    return f"moderation:ip-ban:{ip}"


def user_ban_cache_key(user):
    return (
        f"moderation:user-ban:{user.pk}:"
        f"{int(getattr(user, 'banned', False))}:"
        f"{user.banned_date.isoformat() if user.banned_date else 'none'}"
    )


def invalidate_device_ban_cache(*fingerprints):
    keys = [device_ban_cache_key(fp) for fp in fingerprints if fp]
    if keys:
        cache_delete_many(keys)


def invalidate_ip_ban_cache(*ips):
    keys = [ip_ban_cache_key(ip) for ip in ips if ip]
    if keys:
        cache_delete_many(keys)


def invalidate_user_ban_cache(user):
    if user and getattr(user, "pk", None):
        cache.delete(user_ban_cache_key(user))


def get_device_ban_result(*fingerprints):
    clean_fps = [fp for fp in dict.fromkeys(fingerprints) if fp]
    if not clean_fps:
        return DeviceBanResult()

    missed = []
    for fp in clean_fps:
        cached = cache.get(device_ban_cache_key(fp))
        if cached is None:
            missed.append(fp)
            continue
        if cached.get("banned"):
            return DeviceBanResult(True, cached.get("reason"), fp)

    if missed:
        bans = {
            ban["fingerprint"]: ban
            for ban in DeviceBan.objects.filter(
                fingerprint__in=missed,
                active=True,
            ).values("fingerprint", "reason")
        }
        for fp in missed:
            ban = bans.get(fp)
            cache.set(
                device_ban_cache_key(fp),
                {"banned": bool(ban), "reason": ban["reason"] if ban else None},
                DEVICE_CACHE_TIMEOUT,
            )
            if ban:
                return DeviceBanResult(True, ban["reason"], fp)

    return DeviceBanResult()


def is_ip_banned(ip):
    if not ip:
        return False

    cached = cache.get(ip_ban_cache_key(ip))
    if cached is not None:
        return bool(cached)

    banned = BannedIps.objects.filter(ip_address=ip).exists()
    cache.set(ip_ban_cache_key(ip), banned, IP_CACHE_TIMEOUT)
    return banned


def is_user_banned(user):
    if not user.is_authenticated:
        return False

    cached = cache.get(user_ban_cache_key(user))
    if cached is not None:
        return bool(cached)

    banned = False
    if user.banned:
        if user.banned_date is None or user.banned_date > timezone.now():
            banned = True
        else:
            updated = user.__class__.objects.filter(
                pk=user.pk,
                banned=True,
                banned_date__lte=timezone.now(),
            ).update(banned=False, banned_reason="", banned_date=None)
            if updated:
                user.banned = False
                user.banned_reason = ""
                user.banned_date = None

    cache.set(user_ban_cache_key(user), banned, USER_BAN_CACHE_TIMEOUT)
    return banned


def should_check_moderation(request):
    return not request.path.startswith(("/api-admin/", "/admin/"))


def get_request_device_data(request):
    device_fp = getattr(request, "device_fingerprint", None)
    if not device_fp:
        device_fp, was_generated = get_device_fingerprint(request)
        request.device_fingerprint = device_fp
        request._device_fp = device_fp
        request._device_fp_generated = was_generated

    derived_fp = getattr(request, "derived_device_fp", None)
    if not derived_fp:
        derived_fp = derive_device_fingerprint(request)
        request.derived_device_fp = derived_fp
        request._derived_fp = derived_fp

    return device_fp, derived_fp


def get_request_device_ban(request):
    if not should_check_moderation(request):
        return DeviceBanResult()

    device_fp, derived_fp = get_request_device_data(request)
    if getattr(request, "_device_fp_generated", False) and not derived_fp:
        return DeviceBanResult()
    return get_device_ban_result(device_fp, derived_fp)


def record_device_activity(request):
    device_fp = getattr(request, "_device_fp", None)
    derived_fp = getattr(request, "_derived_fp", None)
    was_generated = getattr(request, "_device_fp_generated", False)
    ip_for_storage = getattr(request, "_ip_for_storage", None)
    user_agent = getattr(request, "_user_agent", "")

    chosen_fp = None
    if device_fp and not was_generated:
        chosen_fp = device_fp
    elif derived_fp:
        chosen_fp = derived_fp
    else:
        chosen_fp = device_fp

    if not chosen_fp:
        return

    if not request.user.is_authenticated:
        return

    user_id = request.user.pk if request.user.is_authenticated else "anon"
    cache_key = f"moderation:device-activity:{chosen_fp}:{user_id}:{ip_for_storage}"
    if cache.get(cache_key):
        return
    cache.set(cache_key, True, DEVICE_ACTIVITY_TIMEOUT)

    dev, created = Device.objects.get_or_create(
        fingerprint=chosen_fp,
        defaults={
            "last_ip": ip_for_storage,
            "user_agent": user_agent[:1000],
            "last_user": request.user if request.user.is_authenticated else None,
            "seen_count": 1,
        },
    )

    if not created:
        update_fields = ["last_seen", "seen_count"]
        dev.last_seen = timezone.now()
        dev.seen_count = dev.seen_count + 1

        if ip_for_storage and dev.last_ip != ip_for_storage:
            dev.last_ip = ip_for_storage
            update_fields.append("last_ip")

        if user_agent and dev.user_agent != user_agent[:1000]:
            dev.user_agent = user_agent[:1000]
            update_fields.append("user_agent")

        if request.user.is_authenticated and dev.last_user_id != request.user.pk:
            dev.last_user = request.user
            update_fields.append("last_user")

        dev.save(update_fields=update_fields)

    if request.user.is_authenticated:
        usage, created = DeviceUsage.objects.get_or_create(
            device=dev,
            user=request.user,
            defaults={"usage_count": 1},
        )
        if not created:
            usage.last_seen = timezone.now()
            usage.usage_count = usage.usage_count + 1
            usage.save(update_fields=["last_seen", "usage_count"])


def create_device_bans_for_user(user, reason=None):
    fingerprints = set(
        Device.objects.filter(Q(last_user=user) | Q(usages__user=user))
        .values_list("fingerprint", flat=True)
        .distinct()
    )
    if not fingerprints:
        return 0

    created_or_updated = 0
    for fingerprint in fingerprints:
        _, created = DeviceBan.objects.update_or_create(
            fingerprint=fingerprint,
            defaults={
                "reason": reason,
                "related_user": user,
                "active": True,
            },
        )
        created_or_updated += 1 if created else 0

    invalidate_device_ban_cache(*fingerprints)
    return created_or_updated
