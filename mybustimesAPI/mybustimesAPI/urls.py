from django.contrib import admin
from django.urls import path, include
from mybustimes.views import *
from django.conf.urls.static import static

ad_list = adViewSet.as_view({'get': 'list'})
ad_detail = adViewSet.as_view({'get': 'retrieve'})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', ApiRootView.as_view(), name='api-root'),
    path('api/users/', include('mybustimes.urls')),
    path('api/themes/', themeListView.as_view(), name='theme-list'),
    path('api/themes/<int:pk>/', themeDetailView.as_view(), name='theme-detail'),
    path('api/fleet/', fleetListView.as_view(), name='fleet-list'),
    path('api/fleet/<int:pk>/', fleetDetailView.as_view(), name='fleet-detail'),
    path('api/operators/', operatorListView.as_view(), name='operators-list'),
    path('api/operators/<str:name>/', operatorDetailView.as_view(), name='operators-detail'),
    path('api/operators/<int:pk>/', operatorDetailView.as_view(), name='operators-detail'),
    path('api/liveries/', liveriesListView.as_view(), name='liveries-list'),
    path('api/liveries/<int:pk>/', liveriesDetailView.as_view(), name='liveries-detail'),
    path('api/type/', typeListView.as_view(), name='type-list'),
    path('api/type/<int:pk>/', typeDetailView.as_view(), name='type-detail'),
    path('api/groups/', groupsListView.as_view(), name='groups-list'),
    path('api/groups/<int:pk>/', groupsDetailView.as_view(), name='groups-detail'),
    path('api/organisations/', organisationsListView.as_view(), name='organisations-list'),
    path('api/organisations/<int:pk>/', organisationsDetailView.as_view(), name='organisations-detail'),
    path('api/regions/', regionsListView.as_view(), name='regions-list'),
    path('api/regions/<str:region_code>/', regionsDetailView.as_view(), name='regions-detail'),
    path('api/routes/', routesListView.as_view(), name='routes-list'),
    path('api/routes/<int:pk>/', routesDetailView.as_view(), name='routes-detail'),
    path('api/ads/', ad_list, name='ads-list'),
    path('api/ads/<int:pk>/', ad_detail, name='ads-detail'),
    path('api/badges/', badgesListView.as_view(), name='badges-list'),
    path('api/badges/<int:pk>/', badgesDetailView.as_view(), name='badges-detail'),
    path('api/feature-toggles/', FeatureToggleView.as_view(), name='feature-toggles'),
    path('api/helper-perms/', helperPermsListView.as_view(), name='helperPerm'),
    path('api/helper-perms/<int:pk>/', helperPermsDetailView.as_view(), name='helperPerm'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)