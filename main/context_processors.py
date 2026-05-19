from datetime import datetime, timedelta
import json
import logging

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from main import moderation
from main.models import theme, ad, google_ad, featureToggle, ActiveSubscription
from mybustimes import settings

logger = logging.getLogger(__name__)

User = get_user_model()

# Constants
CACHE_TIMEOUT = 300  # 5 minutes
DEFAULT_BRAND_COLOUR = '8cb9d5'
DEFAULT_THEME = 'MBT_Light.css'

# Favicon URL constants
CDN_BASE = 'https://cdn.mybustimes.cc'
FAVICON_PATHS = {
    'default': {
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
    },
    'spm': f'{CDN_BASE}/mybustimes/staticfiles/src/icons/favicon/MBTSPM.png',
    'poppy': f'{CDN_BASE}/assets/Square%20Small%20Icon.svg',
    'christmas': f'{CDN_BASE}/assets/Christmas/Square Small Icon.svg',
}


def get_online_users_count(minutes=10):
    """Get count of users active in last N minutes."""
    cutoff = timezone.now() - timedelta(minutes=minutes)
    return User.objects.filter(last_active__gte=cutoff, is_active=True).count()


def get_total_users_count():
    """Get total active users count."""
    return User.objects.filter(is_active=True).count()


def get_cached_or_query(cache_key, query_func, timeout=CACHE_TIMEOUT):
    """Generic cache getter with fallback to query function."""
    data = cache.get(cache_key)
    if data is None:
        data = query_func()
        cache.set(cache_key, data, timeout)
    return data


def get_theme_data(include_suggested=False):
    """Get all theme-related data with caching."""
    all_themes = get_cached_or_query(
        'all_themes:v2',
        lambda: list(theme.objects.all().order_by('weight').values(
            'id',
            'theme_name',
            'light_main_colour',
            'sugggested',
        ))
    )
    suggested = None
    if include_suggested:
        suggested = next((t for t in all_themes if t.get('sugggested')), None)
    return suggested, all_themes


def get_ad_data(request):
    """Get ad data with caching and URL transformation."""
    cached_ads = get_cached_or_query(
        'live_ads',
        lambda: list(ad.objects.filter(ad_live=True).values('ad_name', 'ad_img', 'ad_link', 'ad_img_overide'))
    )
    
    # Transform ad image URLs
    live_ads = [a.copy() for a in cached_ads]
    for a in live_ads:
        media_path = settings.MEDIA_URL + a['ad_img']
        a['ad_img'] = request.build_absolute_uri(media_path)
    
    google_ads = get_cached_or_query(
        'google_ads',
        lambda: {g.ad_place_id: g.ad_id for g in google_ad.objects.all()}
    )
    
    live_ads_json = json.dumps(live_ads)
    google_ads_json = json.dumps(google_ads)
    
    return live_ads_json, google_ads_json


def get_feature_toggles():
    """Get all ad-related feature toggles with caching."""
    flags = get_cached_or_query(
        'feature_toggle_flags',
        lambda: set(featureToggle.objects.filter(enabled=True).values_list('name', flat=True))
    )
    return 'google_ads' in flags, 'mbt_ads' in flags, 'ads' in flags


def check_user_subscription(user):
    """Check if user has active subscription with caching."""
    if not user.is_authenticated:
        return False
    
    cache_key = f'user_{user.id}_active_sub'
    has_active_sub = cache.get(cache_key)
    
    if has_active_sub is None:
        has_active_sub = ActiveSubscription.objects.filter(
            user=user
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gt=timezone.now())
        ).exists()
        cache.set(cache_key, has_active_sub, CACHE_TIMEOUT)
    
    return has_active_sub


def get_special_events():
    """Calculate all special events for current date/time."""
    now = datetime.now()
    return {
        'spm': now.month == 9,
        'pride_month': now.month == 6,
        'birthday': now.month == 8 and now.day == 7,
        'halloween': now.month == 10 and now.day == 31,
        'christmas': now.month == 12,
        'poppy': now.month == 11,
        'silence': now.month == 11 and now.day == 11 and now.hour == 11 and now.minute in [0, 1],
    }


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


def get_user_theme_settings(user):
    """Extract theme settings from user profile."""
    if not user.is_authenticated or not user.theme_id:
        return None, 'False', DEFAULT_BRAND_COLOUR, False

    theme_data = get_cached_or_query(
        f'user_theme_data:{user.theme_id}',
        lambda: theme.objects.filter(pk=user.theme_id).values(
            'light_css',
            'dark_css',
            'light_main_colour',
            'dark_main_colour',
            'sugggested',
        ).first(),
        timeout=900,
    )
    if not theme_data:
        return None, 'False', DEFAULT_BRAND_COLOUR, False
    
    suggested = theme_data['sugggested']
    dark_mode = 'True' if getattr(user, "dark_mode", False) else 'False'
    
    if dark_mode == 'True' and theme_data['dark_css']:
        theme_filename = theme_data['dark_css'].split('/')[-1]
        brand_colour = theme_data['dark_main_colour'] or DEFAULT_BRAND_COLOUR
    elif theme_data['light_css']:
        theme_filename = theme_data['light_css'].split('/')[-1]
        brand_colour = theme_data['light_main_colour'] or DEFAULT_BRAND_COLOUR
    else:
        theme_filename = DEFAULT_THEME
        brand_colour = DEFAULT_BRAND_COLOUR
    
    return theme_filename, dark_mode, brand_colour, suggested


def get_cookie_theme_settings(request):
    """Extract theme settings from cookies."""
    dark_mode = request.COOKIES.get('darkMode', 'False')
    brand_colour = request.COOKIES.get('brandColour', DEFAULT_BRAND_COLOUR)
    
    if dark_mode == 'True':
        theme_filename = request.COOKIES.get('themeDarkCSS', DEFAULT_THEME)
    else:
        theme_filename = request.COOKIES.get('themeLight', DEFAULT_THEME)
    
    return theme_filename, dark_mode, brand_colour


def check_ban_status(user, ip):
    """Check if user or IP is banned."""
    return moderation.is_ip_banned(ip), moderation.is_user_banned(user)


def check_device_ban(request, ip):
    """Check for device bans using multiple methods."""
    device_ban = moderation.get_request_device_ban(request)
    device_fp = getattr(request, 'device_fingerprint', None)
    return device_ban.banned, device_ban.reason, device_fp


def should_disable_ads(request):
    """Check if ads should be disabled for current path."""
    path = request.path.lower()
    return any(path.endswith(suffix) for suffix in [
        '/stops/edit/inbound/',
        '/stops/edit/outbound/',
        '/stops/add/inbound/',
        '/stops/add/outbound/',
        '/help/',
        '/map/',
    ])


def theme_settings(request):
    """Main context processor for theme and site settings."""
    user = request.user
    
    # Get cached data
    suggested_theme_obj, all_themes = get_theme_data(include_suggested=request.path == '/')
    google_ads_enabled, mbt_ads_enabled, ads_enabled = get_feature_toggles()
    ads_disabled_for_path = should_disable_ads(request)
    
    # Check subscription status only if ads might otherwise render.
    has_active_sub = check_user_subscription(user) if ads_enabled and not ads_disabled_for_path else False
    
    # Disable ads if user has subscription or ads are globally disabled
    if has_active_sub or not ads_enabled or ads_disabled_for_path:
        ads_enabled = google_ads_enabled = mbt_ads_enabled = False

    if ads_enabled:
        live_ads_json, google_ads_json = get_ad_data(request)
    else:
        live_ads_json, google_ads_json = '[]', '{}'
    
    # Get special events
    events = get_special_events()
    
    # Theme settings
    if user.is_authenticated and user.theme_id:
        theme_filename, dark_mode, brand_colour, suggested_theme = get_user_theme_settings(user)
    else:
        theme_filename, dark_mode, brand_colour = get_cookie_theme_settings(request)
        suggested_theme = False
    
    # Halloween override
    if events['halloween']:
        theme_filename = 'Halloween_Dark.css'
    
    # Get logos and favicons
    is_dark = dark_mode in ('true', 'True')
    menu_logo, burger_menu_logo = get_logo_urls(is_dark, events)
    favicons = get_favicon_set(events)
    
    # Get user IP
    ip = moderation.get_storage_ip(request)
    
    # Ban checks
    user_has_banned_ip, user_account_banned = check_ban_status(user, ip)
    if getattr(request, 'device_ban_checked', False):
        device_banned = getattr(request, 'device_banned', False)
        device_ban_reason = getattr(request, 'device_ban_reason', None)
        device_fp = getattr(request, 'device_fingerprint', None)
    else:
        device_banned, device_ban_reason, device_fp = check_device_ban(request, ip)
    
    banned = user_has_banned_ip or user_account_banned or device_banned
    
    if request.path.lower().endswith('/help/'):
        banned = user_has_banned_ip = user_account_banned = False
    
    # Admin check
    admin = user.is_authenticated and (user.is_superuser or user.is_staff)
    
    return {
        'has_pro': 'true' if has_active_sub else 'false',
        'banned': banned,
        'unban_date_time': user.banned_date if user.is_authenticated and user.banned_date else None,
        'ban_reason': user.banned_reason if user.is_authenticated else None,
        'ip_banned': user_has_banned_ip,
        'user_banned': user_account_banned,
        'theme': theme_filename,
        'themeDark': dark_mode,
        'suggested_theme': suggested_theme,
        'suggested_theme_obj': suggested_theme_obj,
        'brand_colour': brand_colour,
        'menuLogo': menu_logo,
        'burgerMenuLogo': burger_menu_logo,
        'current_year': datetime.now().year,
        'all_themes': all_themes,
        'live_ads': live_ads_json,
        'google_ads': google_ads_json,
        'google_ads_enabled': google_ads_enabled,
        'mbt_ads_enabled': mbt_ads_enabled,
        'ads_enabled': ads_enabled,
        'admin': admin,
        'device_banned': device_banned,
        'device_ban_reason': device_ban_reason,
        'device_fp': device_fp,
        'CF_SITE_KEY': settings.CF_SITE_KEY,
        'STRIPE_BILLING_PORTAL_URL': settings.STRIPE_BILLING_PORTAL_URL,
        'favicon_ico': favicons['ico'],
        'favicon_svg': favicons['svg'],
        'favicon_96x96': favicons['96x96'],
        'favicon_32x32': favicons['32x32'],
        'favicon_16x16': favicons['16x16'],
        'favicon_touch': favicons['touch'],
        'apple_icon_57x57': favicons['apple_57'],
        'apple_icon_60x60': favicons['apple_60'],
        'apple_icon_72x72': favicons['apple_72'],
        'apple_icon_76x76': favicons['apple_76'],
        'apple_icon_114x114': favicons['apple_114'],
        'apple_icon_120x120': favicons['apple_120'],
        'apple_icon_144x144': favicons['apple_144'],
        'apple_icon_152x152': favicons['apple_152'],
        'apple_icon_180x180': favicons['apple_180'],
        'android_icon_192x192': favicons['android_192'],
        'ms_icon_144x144': favicons['ms_144'],
        'manifest_json': favicons['manifest'],
        'silence': events['silence'],
        'ACKEE_DOMAIN_ID': settings.ACKEE_DOMAIN_ID,
    }
