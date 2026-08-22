from django.urls import path, include
from django.contrib import admin
from django.views.i18n import JavaScriptCatalog

urlpatterns = [
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    path('admin/', include((admin.site.get_urls(), 'admin'), namespace='docs_admin')),
    path('filer/', include('filer.urls')),
    path('', include('cms.urls')),
]
