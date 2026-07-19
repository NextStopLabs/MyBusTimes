from urllib import response
import re
from django.shortcuts import render, redirect
from django.urls import resolve
from .models import featureToggle
from tracking.models import Trip
import requests
import traceback
from fleet.models import fleet, fleetChange, vehicleType, MBTOperator
from routes.models import route
from django.contrib.sessions.models import Session
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.utils.timezone import now, timedelta
from django.contrib.auth import get_user_model
from django.http import Http404
from django.db import DatabaseError
from django.db.models import Q
from django.core.cache import cache
from .feature_bans import FEATURE_BAN_PATH_RULES, FEATURE_BAN_REGEX_RULES

MAX_ACTIVE_USERS = 100
ACTIVE_TIME_WINDOW = timedelta(minutes=2)
User = get_user_model()

EXEMPT_PATHS = ['/admin/', '/account/login/', '/queue/', '/ads.txt', '/robots.txt']
API_SKIP_PREFIXES = ['/api/']
FEATURE_CACHE_TTL = 60


def get_feature_ban_for_path(path):
    for ban_name, prefixes in FEATURE_BAN_PATH_RULES.items():
        if any(path.startswith(prefix) for prefix in prefixes):
            return ban_name
    for ban_name, patterns in FEATURE_BAN_REGEX_RULES.items():
        if any(re.match(pattern, path) for pattern in patterns):
            return ban_name
    return None


def is_feature_enabled(name):
    cached_flags = cache.get('feature_toggle_flags')
    if cached_flags is None:
        cached_flags = set(featureToggle.objects.filter(enabled=True).values_list('name', flat=True))
        cache.set('feature_toggle_flags', cached_flags, FEATURE_CACHE_TTL)
    return name in cached_flags

class QueueMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            if request.path.startswith(('/admin/', '/account/login/', '/queue/', '/u/register/', '/account/register/', '/static/', '/media/', '/api/')):
                return self.get_response(request)

            if is_feature_enabled('queue_system') and not request.user.is_superuser:

                if not request.user.is_authenticated:
                    return redirect('/account/login/')  # or allow anonymously with a fallback

                if request.session.get('queue_pass'):
                    return self.get_response(request)

                now_time = now()
                user_last_active = request.user.last_active
                if user_last_active:
                    position = User.objects.filter(
                        last_active__gte=now_time - ACTIVE_TIME_WINDOW
                    ).filter(
                        Q(last_active__lt=user_last_active) |
                        Q(last_active=user_last_active, id__lte=request.user.id)
                    ).count()
                else:
                    position = None

                if position is not None and position <= MAX_ACTIVE_USERS:
                    request.session['queue_pass'] = True
                    return self.get_response(request)
                else:
                    request.session['queue_position'] = position
                    return redirect('/queue/')
        
        except DatabaseError:
            pass

        return self.get_response(request)

class FeatureBanMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(('/admin/', '/api-admin/', '/account/login/', '/static/', '/media/', '/api/')):
            return self.get_response(request)

        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated or user.is_superuser:
            return self.get_response(request)

        ban_name = get_feature_ban_for_path(request.path)
        if not ban_name:
            return self.get_response(request)

        try:
            if user.banned_from.filter(name=ban_name).exists():
                return render(request, 'error/403.html', status=403)
        except DatabaseError:
            pass

        return self.get_response(request)

class SiteImportingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(tuple(API_SKIP_PREFIXES)):
            return self.get_response(request)

        # Exempt login and admin pages
        exempt_paths = EXEMPT_PATHS
        if any(request.path.startswith(path) for path in exempt_paths):
            return self.get_response(request)

        try:
            if is_feature_enabled('importing_data') and not request.user.is_superuser:
                counts = cache.get('site_import_counts')
                if counts is None:
                    counts = {
                        'fleet_changes': fleetChange.objects.count(),
                        'routes_imported': route.objects.count(),
                        'vehicles_imported': fleet.objects.count(),
                        'trips_imported': Trip.objects.count(),
                        'vehicleTypes': vehicleType.objects.count(),
                        'operators': MBTOperator.objects.count(),
                    }
                    cache.set('site_import_counts', counts, 30)

                return render(request, 'site_importing.html', counts, status=200)
        except DatabaseError:
            pass

        return self.get_response(request)

class SiteLockMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(tuple(API_SKIP_PREFIXES)):
            return self.get_response(request)

        # Exempt login and admin pages
        exempt_paths = EXEMPT_PATHS
        if any(request.path.startswith(path) for path in exempt_paths):
            return self.get_response(request)

        try:
            if is_feature_enabled('full_admin_only') and not request.user.is_superuser:

                return render(request, 'site_locked.html', status=200)
        except DatabaseError:
            pass

        return self.get_response(request)

class SiteUpdatingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(tuple(API_SKIP_PREFIXES)):
            return self.get_response(request)

        # Exempt login and admin pages
        exempt_paths = EXEMPT_PATHS
        if any(request.path.startswith(path) for path in exempt_paths):
            return self.get_response(request)

        try:
            if is_feature_enabled('site_updating') and not request.user.is_superuser:

                return render(request, 'site_updating.html', status=200)
        except DatabaseError:
            pass

        return self.get_response(request)
    
class CustomErrorMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if isinstance(exception, Http404):
            # Let Django handle it normally, or defer to process_response
            return None

        # Otherwise, handle as 500
        tb = traceback.format_exc()
        user = getattr(request, 'user', None)
        user_info = f"{user} (id={user.id})" if user and user.is_authenticated else "Anonymous User"
        full_url = request.build_absolute_uri()

        tb_full = tb

        if len(tb) > 1900:
            tb = tb[:1900] + "\n... (truncated)"

        content = (
            f"**500 Error**\n"
            f"**User:** {user_info}\n"
            f"**URL:** {full_url}\n"
            f"```\n{tb}\n```"
        )

        try:
            requests.post(settings.DISCORD_WEB_ERROR_WEBHOOK, json={"content": content}, timeout=5)
        except Exception:
            pass

        return render(request, 'error/500.html', {'debug_traceback': tb_full}, status=500)

    def process_response(self, request, response):
        if response.status_code in [401, 403, 404, 501, 502]:
            user = getattr(request, 'user', None)
            user_info = f"{user} (id={user.id})" if user and user.is_authenticated else "Anonymous User"

            if response.status_code == 404 and (not user or not user.is_authenticated):
                return response

            full_url = request.build_absolute_uri()

            content = (
                f"**{response.status_code} Error**\n"
                f"**User:** {user_info}\n"
                f"**URL:** {full_url}\n"
                f"```\nNo traceback available.\n```"
            )

            try:
                webhook = settings.DISCORD_404_ERROR_WEBHOOK if response.status_code == 404 or response.status_code == 403 else settings.DISCORD_WEB_ERROR_WEBHOOK
                requests.post(webhook, json={"content": content}, timeout=5)
            except Exception:
                pass

            return render(request, f'error/{response.status_code}.html', status=response.status_code)

        return response
    
class StaffOnlyDocsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/docs/") and not request.user.is_staff:
            return render(request, "error/403.html", status=403)
        return self.get_response(request)
