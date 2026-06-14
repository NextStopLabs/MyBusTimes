from datetime import timedelta
import json
import logging

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from main import moderation
from main.discord_roles import user_is_discord_booster
from main.models import theme, ad, google_ad, featureToggle, ActiveSubscription
from mybustimes import settings

logger = logging.getLogger(__name__)
User = get_user_model()

CACHE_TIMEOUT = 300
DEFAULT_BRAND_COLOUR = '8cb9d5'
DEFAULT_THEME = 'MBT_Light.css'
PRO_PLANS = {'pro', 'premium'}

CDN_BASE = 'https://cdn.mybustimes.cc'

# Exempt paths from moderation checks (static, admin, api, etc.)
_MODERATION_EXEMPT_PREFIXES = ('/static/', '/media/', '/admin/', '/api-admin/', '/api/', '/account/login/')

# ✅ Precomputed favicon defaults (never rebuild)
FAVICON_DEFAULT = {
    'ico': f'{CDN_BASE}/assets/main/favicons/favicon.ico',
    'svg': f'{CDN_BASE}/assets/main/icon.svg',
    '96x96': f'{CDN_BASE}/assets/main/favicons/favicon-96x96.png',
    '32x32': f'{CDN_BASE}/assets/main/favicons/favicon-32x32.png',
    '16x16': f'{CDN_BASE}/assets/main/favicons/favicon-16x16.png',
    'touch': f'{CDN_BASE}/assets/main/favicons/apple-icon.png',
    'apple_57': f'{CDN_BASE}/assets/main/favicons/apple-icon-57x57.png',
    'apple_60': f'{CDN_BASE}/assets/main/favicons/apple-icon-60x60.png',
    'apple_72': f'{CDN_BASE}/assets/main/favicons/apple-icon-72x72.png',
    'apple_76': f'{CDN_BASE}/assets/main/favicons/apple-icon-76x76.png',
    'apple_114': f'{CDN_BASE}/assets/main/favicons/apple-icon-114x114.png',
    'apple_120': f'{CDN_BASE}/assets/main/favicons/apple-icon-120x120.png',
    'apple_144': f'{CDN_BASE}/assets/main/favicons/apple-icon-144x144.png',
    'apple_152': f'{CDN_BASE}/assets/main/favicons/apple-icon-152x152.png',
    'apple_180': f'{CDN_BASE}/assets/main/favicons/apple-icon-180x180.png',
    'android_192': f'{CDN_BASE}/assets/main/favicons/android-icon-192x192.png',
    'ms_144': f'{CDN_BASE}/assets/main/favicons/ms-icon-144x144.png',
    'manifest': f'{CDN_BASE}/assets/main/favicons/manifest.json',
}

def get_cached(key, fn, timeout=CACHE_TIMEOUT):
    val = cache.get(key)
    if val is None:
        val = fn()
        cache.set(key, val, timeout)
    return val

def get_logo_urls(dark_mode, events):
    """Get menu and burger menu logo URLs based on mode and events."""
    burger_logo = (
        f'{CDN_BASE}/mybustimes/staticfiles/src/icons/Burger-Menu-White.webp'
        if dark_mode else
        f'{CDN_BASE}/mybustimes/staticfiles/src/icons/Burger-Menu-Black.webp'
    )
    
    # Logo priority: SPM > Poppy > Christmas > Birthday > Pride > Default
    if events['spm']:
        suffix = 'White-SPM.png' if dark_mode else 'Black-SPM.png'
        menu_logo = f'{CDN_BASE}/mybustimes/staticfiles/src/icons/MBT-Logo-{suffix}'
    elif events['poppy']:
        menu_logo = f'{CDN_BASE}/assets/Logo Light.svg' if dark_mode else f'{CDN_BASE}/assets/Logo Dark.svg'
    elif events['christmas']:
        menu_logo = f'{CDN_BASE}/assets/Christmas/Logo.svg'
    elif events['birthday']:
        suffix = 'White-BD.png' if dark_mode else 'Black-BD.png'
        menu_logo = f'{CDN_BASE}/mybustimes/staticfiles/src/icons/MBT-Logo-{suffix}'
    elif events['pride_month']:
        menu_logo = 'https://raw.githubusercontent.com/Kai-codin/MBT-Media-Kit/refs/heads/main/MBT%20Logos/MBT-Logo-Pride-MMH-outline-2.webp'
    else:
        menu_logo = f'{CDN_BASE}/assets/main/Logo.svg' if dark_mode else f'{CDN_BASE}/assets/main/Logo-Dark.svg'
    
    return menu_logo, burger_logo


def get_favicon_set(events):
    """Get complete favicon set based on special events."""
    if events['spm']:
        icon = FAVICON_PATHS['spm']
        return {k: icon for k in FAVICON_PATHS['default'].keys()}
    elif events['poppy']:
        icon = FAVICON_PATHS['poppy']
        return {k: icon for k in FAVICON_PATHS['default'].keys()}
    elif events['christmas']:
        icon = FAVICON_PATHS['christmas']
        return {k: icon for k in FAVICON_PATHS['default'].keys()}
    else:
        return FAVICON_PATHS['default']


def theme_settings(request):
    user = request.user
    path = request.path.lower()
    now = timezone.now()

    # --- feature flags ---
    flags = get_cached(
        'feature_flags',
        lambda: set(featureToggle.objects.filter(enabled=True).values_list('name', flat=True))
    )
    google_ads_enabled = 'google_ads' in flags
    mbt_ads_enabled = 'mbt_ads' in flags
    ads_enabled = 'ads' in flags

    # --- subscription ---
    has_active_sub = False
    has_pro = False
    is_discord_booster = False

    if user.is_authenticated:
        cache_key = f'u_sub:{user.id}'
        cached = cache.get(cache_key)

        if cached is None:
            has_active_sub = (
                ActiveSubscription.objects.filter(user=user)
                .filter(Q(end_date__isnull=True) | Q(end_date__gt=now))
                .exists()
                or (
                    getattr(user, 'sub_plan', 'free') != 'free'
                    and user.ad_free_until
                    and user.ad_free_until > now
                )
            )

            is_discord_booster = user_is_discord_booster(user)
            has_active_sub = has_active_sub or is_discord_booster

            has_pro = (
                ActiveSubscription.objects.filter(
                    user=user,
                    end_date__gt=now,
                    plan__in=PRO_PLANS
                ).exists()
                or (
                    getattr(user, 'sub_plan', 'free') in PRO_PLANS
                    and user.ad_free_until
                    and user.ad_free_until > now
                )
            )

            cache.set(cache_key, (has_active_sub, has_pro, is_discord_booster), CACHE_TIMEOUT)
        else:
            if len(cached) == 2:
                has_active_sub, has_pro = cached
                is_discord_booster = False
            else:
                has_active_sub, has_pro, is_discord_booster = cached

    # --- ads ---
    if has_active_sub or not ads_enabled or path.endswith((
        '/stops/edit/inbound/',
        '/stops/edit/outbound/',
        '/stops/add/inbound/',
        '/stops/add/outbound/',
        '/help/',
        '/map/',
    )):
        ads_enabled = google_ads_enabled = mbt_ads_enabled = False
        
    # --- themes ---
    all_themes = get_cached(
        'themes',
        lambda: list(theme.objects.order_by('weight').values(
            'id', 'theme_name', 'light_main_colour', 'sugggested'
        ))
    )

    suggested_theme_obj = next((t for t in all_themes if t.get('sugggested')), None) if path == '/' else None

    if user.is_authenticated and user.theme_id:
        theme_data = get_cached(
            f'theme:{user.theme_id}',
            lambda: theme.objects.filter(pk=user.theme_id).values(
                'light_css', 'dark_css', 'light_main_colour', 'dark_main_colour'
            ).first(),
            900
        )

        dark_mode = getattr(user, "dark_mode", False)
        dark_mode_str = 'True' if dark_mode else 'False'

        if dark_mode and theme_data and theme_data['dark_css']:
            theme_filename = theme_data['dark_css'].split('/')[-1]
            brand_colour = theme_data['dark_main_colour'] or DEFAULT_BRAND_COLOUR
        elif theme_data and theme_data['light_css']:
            theme_filename = theme_data['light_css'].split('/')[-1]
            brand_colour = theme_data['light_main_colour'] or DEFAULT_BRAND_COLOUR
        else:
            theme_filename = DEFAULT_THEME
            brand_colour = DEFAULT_BRAND_COLOUR

    else:
        dark_mode_str = request.COOKIES.get('darkMode', 'False')
        brand_colour = request.COOKIES.get('brandColour', DEFAULT_BRAND_COLOUR)
        theme_filename = request.COOKIES.get(
            'themeDarkCSS' if dark_mode_str == 'True' else 'themeLight',
            DEFAULT_THEME
        )

    # --- events ---
    month = now.month
    day = now.day
    events = {
        'spm': month == 9,
        'pride_month': month == 6,
        'birthday': month == 8 and day == 7,
        'halloween': month == 10 and day == 31,
        'christmas': month == 12,
        'poppy': month == 11,
        'silence': month == 11 and day == 11 and now.hour == 11 and now.minute in (0, 1),
    }

    if events['halloween']:
        theme_filename = 'Halloween_Dark.css'

    is_dark = dark_mode_str in ('true', 'True')

    menu_logo, burger_logo = get_logo_urls(is_dark, events)

    # --- bans (skip for API/static to avoid per-request DB overhead) ---
    if any(path.startswith(p) for p in _MODERATION_EXEMPT_PREFIXES):
        banned = ip_banned = user_banned = False
        device_ban = moderation.DeviceBanResult()
    else:
        ip = moderation.get_storage_ip(request)
        ip_banned = moderation.is_ip_banned(ip) if ip else False
        user_banned = moderation.is_user_banned(user) if user.is_authenticated else False
        device_ban = moderation.get_request_device_ban(request)
        banned = ip_banned or user_banned or device_ban.banned

        if path.endswith('/help/'):
            banned = ip_banned = user_banned = False

    admin = user.is_authenticated and (user.is_staff or user.is_superuser)

    return {
        'has_pro': 'true' if has_pro else 'false',
        'is_discord_booster': is_discord_booster,
        'banned': banned,
        'ip_banned': ip_banned,
        'user_banned': user_banned,
        'theme': theme_filename,
        'themeDark': dark_mode_str,
        'brand_colour': brand_colour,
        'menuLogo': menu_logo,
        'burgerMenuLogo': burger_logo,
        'current_year': now.year,
        'all_themes': all_themes,
        'google_ads_enabled': google_ads_enabled,
        'mbt_ads_enabled': mbt_ads_enabled,
        'ads_enabled': ads_enabled,
        'admin': admin,
        'device_banned': device_ban.banned,
        'device_ban_reason': device_ban.reason,
        'CF_SITE_KEY': settings.CF_SITE_KEY,
        'favicon_ico': FAVICON_DEFAULT['ico'],
        'favicon_svg': FAVICON_DEFAULT['svg'],
        'favicon_96x96': FAVICON_DEFAULT['96x96'],
        'favicon_32x32': FAVICON_DEFAULT['32x32'],
        'favicon_16x16': FAVICON_DEFAULT['16x16'],
        'favicon_touch': FAVICON_DEFAULT['touch'],
        'manifest_json': FAVICON_DEFAULT['manifest'],
        'silence': events['silence'],
        'ACKEE_DOMAIN_ID': settings.ACKEE_DOMAIN_ID,
        'STRIPE_BILLING_PORTAL_URL': settings.STRIPE_BILLING_PORTAL_URL,
    }
