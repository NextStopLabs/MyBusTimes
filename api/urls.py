from django.urls import path
from fleet.views import *
from routes.views import *
from tracking.views import *
from main.views import *
from forum.views import *

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
    path('user/', get_user_profile, name='get_user_profile'),


    path('operator/fleet/', fleetListView.as_view(), name='fleet-list'),
    path('operator/fleet/<int:pk>/', fleetDetailView.as_view(), name='fleet-detail'),
    path('operator/', operatorListView.as_view(), name='operator-list'),
    path('operator/<int:pk>/', operatorDetailView.as_view(), name='operator-detail'),
    path('operator/route/', routesListView.as_view(), name='operator-routes'),
    path('operator/route/<int:pk>/', routesDetailView.as_view(), name='operator-route-detail'),

    path('discord-message/', discord_message, name='discord_message'),
    path("check-thread/<str:discord_channel_id>/", check_thread, name="check_thread"),
    path("create-thread/", create_thread_from_discord, name="create_thread_from_discord"),
]
