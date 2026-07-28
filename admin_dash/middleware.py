from django.shortcuts import redirect
from django.conf import settings
from django.utils import timezone

class RequireOTPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/') or request.path.startswith('/api-admin/'):
            if not request.user.is_authenticated:
                return redirect(settings.LOGIN_URL)

            if getattr(settings, 'DISABLED_ADMIN_2FA_REQUIRED', False):
                return self.get_response(request)

            if not request.user.is_verified():
                return redirect('/account/two_factor/setup/')

            last_verified = request.session.get('otp_admin_verified_at')
            OTP_REVERIFY_SECONDS = getattr(settings, 'OTP_ADMIN_REVERIFY_SECONDS', 0)

            needs_reverify = True
            if last_verified and OTP_REVERIFY_SECONDS > 0:
                elapsed = timezone.now().timestamp() - last_verified
                if elapsed < OTP_REVERIFY_SECONDS:
                    needs_reverify = False

            if needs_reverify:
                # Only set the destination on the first re-verify request, so
                # concurrent requests (AJAX, rapid clicks) don't overwrite it
                if 'otp_admin_next' not in request.session:
                    request.session['otp_admin_next'] = request.get_full_path()
                return redirect('/account/two_factor/reverify/')

            # Refresh the timestamp on every successful request so active
            # browsing sessions don't get interrupted by the fixed window
            if last_verified:
                request.session['otp_admin_verified_at'] = timezone.now().timestamp()

        return self.get_response(request)