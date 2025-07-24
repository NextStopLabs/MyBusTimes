from urllib import response
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

MAX_ACTIVE_USERS = 100
ACTIVE_TIME_WINDOW = timedelta(minutes=2)
User = get_user_model()

EXEMPT_PATHS = ['/admin/', '/account/login/', '/queue/', '/ads.txt', '/robots.txt']

class QueueMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            feature = featureToggle.objects.get(name='queue_system')
            
            if feature.enabled and not request.user.is_superuser:
                if request.path.startswith(('/admin/', '/account/login/', '/queue/', '/u/register/', '/account/register/', '/static/', '/media/')):
                    return self.get_response(request)

                if not request.user.is_authenticated:
                    return redirect('/account/login/')  # or allow anonymously with a fallback

                if request.session.get('queue_pass'):
                    return self.get_response(request)

                now_time = now()
                active_users = User.objects.filter(last_active__gte=now_time - ACTIVE_TIME_WINDOW).order_by('last_active')

                # Get position in queue
                user_list = list(active_users.values_list('id', flat=True))
                position = user_list.index(request.user.id) + 1 if request.user.id in user_list else None

                if position is not None and position <= MAX_ACTIVE_USERS:
                    request.session['queue_pass'] = True
                    return self.get_response(request)
                else:
                    request.session['queue_position'] = position
                    return redirect('/queue/')
        
        except featureToggle.DoesNotExist:
            pass

        return self.get_response(request)

class SiteImportingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Exempt login and admin pages
        exempt_paths = EXEMPT_PATHS
        if any(request.path.startswith(path) for path in exempt_paths):
            return self.get_response(request)

        try:
            feature = featureToggle.objects.get(name='importing_data')
            if feature.enabled and not request.user.is_superuser:
                fleet_changes = fleetChange.objects.count()
                routes_imported = route.objects.count()
                vehicles_imported = fleet.objects.count()
                trips_imported = Trip.objects.count()
                vehicleTypes = vehicleType.objects.count()
                operators = MBTOperator.objects.count()

                context = {
                    'trips_imported': trips_imported,
                    'vehicles_imported': vehicles_imported,
                    'routes_imported': routes_imported,
                    'fleet_changes': fleet_changes,
                    'vehicleTypes': vehicleTypes,
                    'operators': operators,
                }

                return render(request, 'site_importing.html', context, status=401)
        except featureToggle.DoesNotExist:
            pass

        return self.get_response(request)

class SiteLockMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Exempt login and admin pages
        exempt_paths = EXEMPT_PATHS
        if any(request.path.startswith(path) for path in exempt_paths):
            return self.get_response(request)

        try:
            feature = featureToggle.objects.get(name='importing_data')
            if feature.enabled and not request.user.is_superuser:

                return render(request, 'site_locked.html', status=401)
        except featureToggle.DoesNotExist:
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

        return render(request, 'error/500.html', {'debug_traceback': tb}, status=500)

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
                webhook = settings.DISCORD_404_ERROR_WEBHOOK if response.status_code == 404 else settings.DISCORD_WEB_ERROR_WEBHOOK
                requests.post(webhook, json={"content": content}, timeout=5)
            except Exception:
                pass

            return render(request, f'error/{response.status_code}.html', status=response.status_code)

        return response