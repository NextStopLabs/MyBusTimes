from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from mybustimes import settings
import debug_toolbar
from django.conf import settings
from django.urls import include, path
from django.views.decorators.cache import cache_control
from django.views.generic.base import RedirectView
from two_factor.urls import urlpatterns as tf_urls
from django_otp.admin import OTPAdminSite
from account.views import disconnect_discord_account, discord_oauth_callback, link_discord_account

if not getattr(settings, 'DISABLED_ADMIN_2FA_REQUIRED', False):
    admin.site.__class__ = OTPAdminSite

urlpatterns = [
    path('account/', include('account.urls')),  # Must be before two_factor.urls so /account/login/ hits CustomLoginView
    path('u/', include('account.urls')),  # Include your routes app urls here
    path('', include(tf_urls)),
    path('BusTimes/', RedirectView.as_view(url='/', permanent=False)),
    path('BusTimes/<path:path>', RedirectView.as_view(url='/', permanent=False)),
    path('api-admin/', admin.site.urls),
    path('admin/', include('admin_dash.urls')),  # Include your admin dashboard app urls here
    path('account/connections/start/', link_discord_account, name='account_connections_start'),
    path('account/connections/callback/', discord_oauth_callback, name='account_connections_callback'),
    path('account/connections/disconnect/', disconnect_discord_account, name='account_connections_disconnect'),
    path('discord/link/', link_discord_account, name='discord_link_account_root'),
    path('discord/callback/', discord_oauth_callback, name='discord_oauth_callback_root'),
    path('discord/disconnect/', disconnect_discord_account, name='discord_disconnect_account_root'),
    path('operator/', include('fleet.urls')),  # Include your operator app urls here
    path('group/', include('group.urls')),  # Include your group app urls here
    path('api/', include('api.urls')),  # Include your API app urls here
    path('organisation/', include('organisation.urls')),  # Include your organisation app urls here
    path("stop/", include('routes.urls')),
    path("tracking/", include('tracking.urls')),
    path("message/", include("messaging.urls")),
    path("apply/", include('apply.urls')),  # Include your apply app urls here
    path("forum/", include('forum.urls')),  # Include your forum app urls here
    path("wiki/", include('wiki.urls')),  # Include your wiki app urls here
    path('select2/', include('django_select2.urls')),
    path('markdownx/', include('markdownx.urls')),
    path('tickets/', include('tickets.urls')),  # Include your tickets app urls here
    path('a/', include('a.urls')),
    path('docs/', include('docs.urls')),
    path('invite/', include('from.urls')),
    path('oidc/', include('mozilla_django_oidc.urls')),
    path('giveaway/', include('giveaway.urls')),  # Include your giveaway app urls here
    path('', include('main.urls')),  # Include your main app urls here
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_URL)

if settings.DEBUG:
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
