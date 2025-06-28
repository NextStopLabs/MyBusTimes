from django.urls import path
from fleet.views import *
from routes.views import *
from tracking.views import *
from main.views import *

urlpatterns = [
    path('liveries/', liveriesListView.as_view(), name='liveries-list'),
    path('liveries/<int:pk>/', liveriesDetailView.as_view(), name='liveries-detail'),
    path('type/', typeListView.as_view(), name='type-list'),
    path('type/<int:pk>/', typeDetailView.as_view(), name='type-detail'),
    path('routes/<int:pk>/stops/', routeStops.as_view(), name='route-stops'),
    path('get_timetables/', get_timetables, name='get_timetables'),
    path('get_trip_times/', get_trip_times, name='get_trip_times'),
    path('active_trips/', map_view.as_view(), name='active_trips'),
    path('service-updates/', siteUpdateListView.as_view(), name='service_updates'),
]
