from django.shortcuts import render
from django.urls import resolve
from .models import featureToggle

class SiteLockMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Exempt login and admin pages
        exempt_paths = ['/account/login/', '/admin/login/']
        if any(request.path.startswith(path) for path in exempt_paths):
            return self.get_response(request)

        try:
            feature = featureToggle.objects.get(name='full_admin_only')
            if feature.enabled and not request.user.is_superuser:
                return render(request, 'site_locked.html', status=401)
        except featureToggle.DoesNotExist:
            pass

        return self.get_response(request)
