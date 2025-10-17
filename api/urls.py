from django.urls import path
from fleet.views import *
from routes.views import *
from tracking.views import *
from main.views import *
from account.views import *
from forum.views import *
from tickets.views import *

from django_ratelimit.decorators import ratelimit

urlpatterns = [
    path('online-vehicles/', ratelimit(key='ip', method='GET', rate='5/s')(online_members), name='online-vehicles'),
    path('liveries/', ratelimit(key='ip', method='GET', rate='2/s')(liveriesListView.as_view()), name='liveries-list'),
    path('liveries/<int:pk>/', ratelimit(key='ip', method='GET', rate='2/s')(liveriesDetailView.as_view()), name='liveries-detail'),
    path('type/', ratelimit(key='ip', method='GET', rate='2/s')(typeListView.as_view()), name='type-list'),
    path('type/<int:pk>/', ratelimit(key='ip', method='GET', rate='2/s')(typeDetailView.as_view()), name='type-detail'),
    path('routes/<int:pk>/stops/', ratelimit(key='ip', method='GET', rate='2/s')(routeStops.as_view()), name='route-stops'),
    path('get_timetables/', ratelimit(key='ip', method='GET', rate='2/s')(get_timetables), name='get_timetables'),
    path('get_trip_times/', ratelimit(key='ip', method='GET', rate='2/s')(get_trip_times), name='get_trip_times'),
    path('active_trips/', ratelimit(key='ip', method='GET', rate='2/s')(map_view.as_view()), name='active_trips'),
    path('service-updates/', ratelimit(key='ip', method='GET', rate='2/s')(siteUpdateListView.as_view()), name='service_updates'),
    path('user/', ratelimit(key='ip', method='GET', rate='2/s')(get_user_profile), name='get_user_profile'),
    path('user-search/', ratelimit(key='ip', method='GET', rate='2/s')(user_search_api), name='user-search-api'),

    path("simplify-gradient/", ratelimit(key='ip', method='GET', rate='2/s')(simplify_gradient), name="simplify_gradient"),

    path("get_random_community_image/", ratelimit(key='ip', method='GET', rate='2/s')(get_random_community_image), name="get_random_community_image"),

    path("thread/<int:thread_id>/", ratelimit(key='ip', method='GET', rate='2/s')(thread_details_api), name="thread_details_api"),

    path('operator/fleet/', ratelimit(key='ip', method='GET', rate='2/s')(fleetListView.as_view()), name='fleet-list'),
    path('operator/fleet/<int:pk>/', ratelimit(key='ip', method='GET', rate='2/s')(fleetDetailView.as_view()), name='fleet-detail'),
    path('operator/', ratelimit(key='ip', method='GET', rate='2/s')(operatorListView.as_view()), name='operator-list'),
    path('operator/<int:pk>/', ratelimit(key='ip', method='GET', rate='2/s')(operatorDetailView.as_view()), name='operator-detail'),
    path('operator/route/', ratelimit(key='ip', method='GET', rate='2/s')(routesListView.as_view()), name='operator-routes'),
    path('operator/route/<int:pk>/', ratelimit(key='ip', method='GET', rate='2/s')(routesDetailView.as_view()), name='operator-route-detail'),
    path('operator/ticket/', ratelimit(key='ip', method='GET', rate='2/s')(ticketListView.as_view()), name='operator-tickets'),
    path('operator/tickle/<int:pk>/', ratelimit(key='ip', method='GET', rate='2/s')(ticketDetailView.as_view()), name='operator-ticket-detail'),

    path('stop/times/', ratelimit(key='ip', method='GET', rate='2/s')(stopUpcomingTripsView.as_view()), name='stop-upcoming-trips'),

    path('discord-message/', ratelimit(key='ip', method='GET', rate='2/s')(discord_message), name='discord_message'),
    path("check-thread/<str:discord_channel_id>/", ratelimit(key='ip', method='GET', rate='2/s')(check_thread), name="check_thread"),
    path("create-thread/", ratelimit(key='ip', method='GET', rate='2/s')(create_thread_from_discord), name="create_thread_from_discord"),

    path("trips/", ratelimit(key='ip', method='GET', rate='2/s')(TripListView.as_view()), name="trip-list"),
    path("trips/create/", ratelimit(key='ip', method='GET', rate='1/m')(StartNewTripView), name="create-trip"),
    path("trips/<int:trip_id>/", ratelimit(key='ip', method='GET', rate='2/s')(TripDetailView.as_view()), name="trip-detail"),

    path("tracking/", ratelimit(key='ip', method='GET', rate='2/s')(TrackingListView.as_view()), name="tracking-list"),
    path("tracking/create/", ratelimit(key='ip', method='GET', rate='1/m')(create_tracking), name="create-tracking-template"),
    path("tracking/<int:tracking_id>/", ratelimit(key='ip', method='GET', rate='2/s')(TrackingDetailView.as_view()), name="tracking-detail"),
    path("tracking/vehicle/<int:vehicle_id>/", ratelimit(key='ip', method='GET', rate='2/s')(TrackingByVehicleView.as_view()), name="tracking-by-vehicle"),

    path('route_trip_eta/', ratelimit(key='ip', method='GET', rate='2/s')(RouteTripETAView.as_view()), name='route_trip_eta'),

    path('user/operators/', ratelimit(key='ip', method='GET', rate='2/s')(get_user_operators), name='get_user_operators'),
    path("user/operator/<int:opID>/fleet/", ratelimit(key='ip', method='GET', rate='2/s')(operator_fleet_view)),
    path("user/operator/<int:opID>/routes/", ratelimit(key='ip', method='GET', rate='2/s')(operator_routes_view)),
    path("user/add_badge/", ratelimit(key='ip', method='GET', rate='2/s')(give_badge)),

    path("all-available-badges/", ratelimit(key='ip', method='GET', rate='2/s')(get_all_available_badges), name="get_all_available_badges"),

    path("tickets/", ratelimit(key='ip', method='GET', rate='2/s')(ticket_list_api), name="ticket_list_api"),

    path("", ratelimit(key='ip', method='GET', rate='2/s')(api_root), name='home'),

    path("key-auth/create-ticket/", ratelimit(key='ip', method='GET', rate='1/m')(create_ticket_api_key_auth), name="create_ticket_api_key_auth"),
    path("key-auth/<int:ticket_id>/messages/", ratelimit(key='ip', method='GET', rate='1/s')(ticket_messages_api_key_auth), name="ticket_messages_api_key_auth"),
    path("<int:ticket_id>/messages/", ratelimit(key='ip', method='GET', rate='1/s')(ticket_messages_api), name="ticket_messages_api"),
]
