from datetime import datetime
from main.models import theme, ad, google_ad, featureToggle, BannedIps
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from mybustimes import settings

import json

User = get_user_model()

def get_online_users_count(minutes=10):
    cutoff = timezone.now() - timedelta(minutes=minutes)
    return User.objects.filter(last_active__gte=cutoff, is_active=True).count()

def get_total_users_count():
    return User.objects.filter(is_active=True).count()

def theme_settings(request):
    user = request.user
    dark_mode = request.COOKIES.get('themeDark', 'false')
    brand_colour = request.COOKIES.get('brandColour', '8cb9d5')
    burger_menu_logo = '/static/src/icons/Burger-Menu-Black.png'  # default

    # Default theme filename and dark_mode fallback
    theme_filename = 'MBT_Light.css'
    
    if user.is_authenticated:
        # Use user's selected theme if available
        if user.theme and user.theme.css:
            theme_filename = user.theme.css.name.split('/')[-1]  # get filename from FileField
        dark_mode = 'True' if user.theme and user.theme.dark_theme else 'False'
        brand_colour = user.theme.main_colour if user.theme else '8cb9d5'  # default to black if no theme
    else:
        # Use cookie values if not logged in
        theme_filename = request.COOKIES.get('theme', theme_filename)
        dark_mode = request.COOKIES.get('themeDark', dark_mode)
        brand_colour = request.COOKIES.get('brandColour', brand_colour)

    if (datetime.now().month == 6):
        pride_month = True
    else:
        pride_month = False

    
    if dark_mode == 'true' or dark_mode == 'True':
        menu_logo = 'https://raw.githubusercontent.com/Kai-codin/MBT-Media-Kit/refs/heads/main/MBT%20Logos/MBT-Logo-White.webp'
        burger_menu_logo = '/static/src/icons/Burger-Menu-White.webp'
    else:
        menu_logo = 'https://raw.githubusercontent.com/Kai-codin/MBT-Media-Kit/refs/heads/main/MBT%20Logos/MBT-Logo-Black.webp'
        burger_menu_logo = '/static/src/icons/Burger-Menu-Black.webp'

    if pride_month:
        menu_logo = 'https://raw.githubusercontent.com/Kai-codin/MBT-Media-Kit/refs/heads/main/MBT%20Logos/MBT-Logo-Pride-MMH-outline-2.webp'

    live_ads = list(ad.objects.filter(ad_live=True).values('ad_name', 'ad_img', 'ad_link', 'ad_img_overide'))
    google_ads = {g.ad_place_id: g.ad_id for g in google_ad.objects.all()}

    live_ads_json = json.dumps(live_ads)  # live_ads is list of dicts
    google_ads_json = json.dumps(google_ads)   

    google_ads_enabled = featureToggle.objects.filter(name='google_ads', enabled=True).exists()
    mbt_ads_enabled = featureToggle.objects.filter(name='mbt_ads', enabled=True).exists()
    ads_enabled = featureToggle.objects.filter(name='ads', enabled=True).exists()

    # Serialize ad_img URL properly
    for a in live_ads:
        media_path = settings.MEDIA_URL + a['ad_img']  # "/media/images/Poly_Bus.webp"
        a['ad_img'] = request.build_absolute_uri(media_path)

    if user.is_authenticated and user.ad_free_until and user.ad_free_until > timezone.now() or ads_enabled == False:  
        ads_enabled = False
        google_ads_enabled = False
        mbt_ads_enabled = False

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

    user_has_banned_ip = BannedIps.objects.filter(ip_address=ip).exists()

    user_account_banned = user.is_authenticated and user.banned

    banned = user_has_banned_ip or user_account_banned

    if user.is_authenticated:
        user_admin_permissions = user.mbt_admin_perms.all()
    else:
        user_admin_permissions = []

    if 'admin_dash' in user_admin_permissions or user.is_superuser:
        admin = True
    else:
        admin = False

    path = request.path.lower()
    if path.endswith('/stops/edit/inbound/') or path.endswith('/stops/edit/outbound/') or \
        path.endswith('/stops/add/inbound/') or path.endswith('/stops/add/outbound/'):
        ads_enabled = False
        google_ads_enabled = False
        mbt_ads_enabled = False

    return {
        'banned': banned,
        'ip_banned': user_has_banned_ip,
        'user_banned': user_account_banned,
        'theme': theme_filename,
        'themeDark': dark_mode,
        'brand_colour': brand_colour,
        'menuLogo': menu_logo,
        'burgerMenuLogo': burger_menu_logo,
        'current_year': datetime.now().year,
        'all_themes': theme.objects.all().order_by('weight'),
        'online_users_count': get_online_users_count(),
        'total_users_count': get_total_users_count(),
        'live_ads': live_ads_json,
        'google_ads': google_ads_json,
        'google_ads_enabled': google_ads_enabled,
        'mbt_ads_enabled': mbt_ads_enabled,
        'ads_enabled': ads_enabled,
        'admin': admin,
    }
