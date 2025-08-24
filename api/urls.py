from django.urls import path
from fleet.views import *
from routes.views import *
from tracking.views import *
from main.views import *
from forum.views import *
from tickets.views import *

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
    path('user-search/', user_search_api, name='user-search-api'),

    path("get_random_community_image/", get_random_community_image, name="get_random_community_image"),

    path("thread/<int:thread_id>/", thread_details_api, name="thread_details_api"),

    path('operator/fleet/', fleetListView.as_view(), name='fleet-list'),
    path('operator/fleet/<int:pk>/', fleetDetailView.as_view(), name='fleet-detail'),
    path('operator/', operatorListView.as_view(), name='operator-list'),
    path('operator/<int:pk>/', operatorDetailView.as_view(), name='operator-detail'),
    path('operator/route/', routesListView.as_view(), name='operator-routes'),
    path('operator/route/<int:pk>/', routesDetailView.as_view(), name='operator-route-detail'),

    path('discord-message/', discord_message, name='discord_message'),
    path("check-thread/<str:discord_channel_id>/", check_thread, name="check_thread"),
    path("create-thread/", create_thread_from_discord, name="create_thread_from_discord"),

    path("trips/", TripListView.as_view(), name="trip-list"),
    path("trips/<int:trip_id>/", TripDetailView.as_view(), name="trip-detail"),

    path("tracking/", TrackingListView.as_view(), name="tracking-list"),
    path("tracking/create/", create_tracking, name="create-tracking-template"),
    path("tracking/<int:tracking_id>/", TrackingDetailView.as_view(), name="tracking-detail"),
    path("tracking/vehicle/<int:vehicle_id>/", TrackingByVehicleView.as_view(), name="tracking-by-vehicle"),

    path('route_trip_eta/', RouteTripETAView.as_view(), name='route_trip_eta'),

    path('user/operators/', get_user_operators, name='get_user_operators'),
    path("user/operator/<int:opID>/fleet/", operator_fleet_view),
    path("user/operator/<int:opID>/routes/", operator_routes_view),

    path("tickets/", ticket_list_api, name="ticket_list_api"),

    path("", api_root, name='home'),

    path("key-auth/<int:ticket_id>/messages/", ticket_messages_api_key_auth, name="ticket_messages_api_key_auth"),
    path("<int:ticket_id>/messages/", ticket_messages_api, name="ticket_messages_api"),
]
