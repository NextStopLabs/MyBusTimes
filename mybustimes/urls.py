from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from mybustimes import settings
import debug_toolbar
from django.conf import settings
from django.urls import include, path

urlpatterns = [
    path('api-admin/', admin.site.urls),
    path('admin/', include('admin_dash.urls')),  # Include your admin dashboard app urls here
    path('operator/', include('fleet.urls')),  # Include your operator app urls here
    path('api/', include('api.urls')),  # Include your API app urls here
    path('account/', include('account.urls')),  # Include your routes app urls here
    path('u/', include('account.urls')),  # Include your routes app urls here
    path("stop/", include('routes.urls')),
    path('', include('main.urls')),  # Include your main app urls here
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]