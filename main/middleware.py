from django.shortcuts import render
from django.urls import resolve
from .models import featureToggle
from tracking.models import Trip
from fleet.models import fleet, fleetChange, vehicleType, MBTOperator
from routes.models import route

class SiteLockMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Exempt login and admin pages
        exempt_paths = ['/account/login/', '/admin/login/', '/ads.txt', '/robots.txt']
        if any(request.path.startswith(path) for path in exempt_paths):
            return self.get_response(request)

        try:
            feature = featureToggle.objects.get(name='full_admin_only')
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
