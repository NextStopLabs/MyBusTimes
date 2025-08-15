from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from mybustimes import settings
import debug_toolbar
from django.conf import settings
from django.urls import include, path
from django.views.decorators.cache import cache_control
from django.views.generic.base import RedirectView

urlpatterns = [
    path('api-admin/', admin.site.urls),
    path('admin/', include('admin_dash.urls')),  # Include your admin dashboard app urls here
    path('operator/', include('fleet.urls')),  # Include your operator app urls here
    path('group/', include('group.urls')),  # Include your group app urls here
    path('api/', include('api.urls')),  # Include your API app urls here
    path('account/', include('account.urls')),  # Include your routes app urls here
    path('u/', include('account.urls')),  # Include your routes app urls here
    path("stop/", include('routes.urls')),
    path("tracking/", include('tracking.urls')),
    path("message/", include("messaging.urls")),
    path("apply/", include('apply.urls')),  # Include your apply app urls here
    path("forum/", include('forum.urls')),  # Include your forum app urls here
    path("wiki/", include('wiki.urls')),  # Include your wiki app urls here
    path('select2/', include('django_select2.urls')),
    path('markdownx/', include('markdownx.urls')),
    path('', include('main.urls')),  # Include your main app urls here
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]