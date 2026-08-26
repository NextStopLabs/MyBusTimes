from django.urls import path
from fleet.views import *
from routes.views import *
from tracking.views import *
from main.views import *
from account.views import *
from forum.views import *
from tickets.views import *
from words.views import *

from django_ratelimit.decorators import ratelimit

urlpatterns = [
    path("liverylab/<int:code>/", ratelimit(key='ip', method='GET', rate='1/s')(getLiveryLab), name="getLiveryLab"),
    path("timetable/<int:route_id>/<str:direction>/", get_timetable, name="timetable-api"),
    path("for-sale-count/", for_sale_count_api, name="for_sale_count_api"),
    path("route/<int:route_id>/timetable-trips/", ratelimit(key='ip', method='GET', rate='10/s')(get_timetable_trips), name="timetable-trips-api"),
    path("routes/timetable-trips/", ratelimit(key='ip', method='GET', rate='10/s')(get_routes_timetable_trips), name="routes-timetable-trips-api"),
    path('check-string/', ratelimit(key='ip', method='GET', rate='5/s')(check_string_view), name='check_string_api'),
    path('online-members/', ratelimit(key='ip', method='GET', rate='5/s')(online_members), name='online-members'),
    path('liveries/', ratelimit(key='ip', method='GET', rate='10/s')(liveriesListView.as_view()), name='liveries-list'),
    path('liveries/<int:pk>/', ratelimit(key='ip', method='GET', rate='10/s')(liveriesDetailView.as_view()), name='liveries-detail'),
    # Board categories - searchable and filterable by operator
    path('board-categories/', ratelimit(key='ip', method='GET', rate='10/s')(boardCategoryListView.as_view()), name='board-categories-list'),
    path('type/', ratelimit(key='ip', method='GET', rate='10/s')(typeListView.as_view()), name='type-list'),
    path('type/<int:pk>/', ratelimit(key='ip', method='GET', rate='10/s')(typeDetailView.as_view()), name='type-detail'),
    path('routes/<int:pk>/stops/', ratelimit(key='ip', method='GET', rate='100/s')(routeStops.as_view()), name='route-stops'),
    path('get_timetables/', ratelimit(key='ip', method='GET', rate='10/s')(get_timetables), name='get_timetables'),
    path('get_trip_times/', ratelimit(key='ip', method='GET', rate='10/s')(get_trip_times), name='get_trip_times'),
    path('active_trips/', ratelimit(key='ip', method='GET', rate='10/s')(map_view.as_view()), name='active_trips'),
    path('service-updates/', ratelimit(key='ip', method='GET', rate='10/s')(siteUpdateListView.as_view()), name='service_updates'),
    path('user/', ratelimit(key='ip', method='GET', rate='10/s')(get_user_profile), name='get_user_profile'),
    path('user-search/', ratelimit(key='ip', method='GET', rate='10/s')(user_search_api), name='user-search-api'),

    path("valhalla/route/", valhalla_proxy, name="valhalla_proxy"),
    path("orr/route/", orr_proxy, name="orr_proxy"),
    
    path("operator/<str:operator_slug>/create-duty/", ratelimit(key='ip', method='POST', rate='10/s')(create_duty_from_timetable_api), name="create-duty-api"),

    path("simplify-gradient/", ratelimit(key='ip', method='GET', rate='10/s')(simplify_gradient), name="simplify_gradient"),

    path("get_random_community_image/", ratelimit(key='ip', method='GET', rate='10/s')(get_random_community_image), name="get_random_community_image"),

    path("thread/<int:thread_id>/", ratelimit(key='ip', method='GET', rate='500/s')(thread_details_api), name="thread_details_api"),

    path('operator/fleet/', ratelimit(key='ip', method='GET', rate='10/s')(fleetListView.as_view()), name='fleet-list'),
    path('operator/fleet/<int:pk>/', ratelimit(key='ip', method='GET', rate='10/s')(fleetDetailView.as_view()), name='fleet-detail'),
    path('operator/', ratelimit(key='ip', method='GET', rate='10/s')(operatorListView.as_view()), name='operator-list'),
    path('operator/<int:pk>/', ratelimit(key='ip', method='GET', rate='10/s')(operatorDetailView.as_view()), name='operator-detail'),
    path('operator/route/', routesListView.as_view(), name='operator-routes'),
    path('operator/route/<int:pk>/', ratelimit(key='ip', method='GET', rate='10/s')(routesDetailView.as_view()), name='operator-route-detail'),
    path('group/<str:group_name>/vehicles/', ratelimit(key='ip', method='GET', rate='10/s')(trackingAPIView.as_view()), name='group-vehicles'),
    path('group/<str:group_name>/routes/', groupRoutesListView.as_view(), name='group-routes'),
    path('operator/ticket/', ratelimit(key='ip', method='GET', rate='10/s')(ticketListView.as_view()), name='operator-tickets'),
    path('operator/tickle/<int:pk>/', ratelimit(key='ip', method='GET', rate='10/s')(ticketDetailView.as_view()), name='operator-ticket-detail'),

    path('stop/times/', ratelimit(key='ip', method='GET', rate='10/s')(stopUpcomingTripsView.as_view()), name='stop-upcoming-trips'),

    path('discord-message/', ratelimit(key='ip', method='GET', rate='10/s')(discord_message), name='discord_message'),
    path("check-thread/<str:discord_channel_id>/", ratelimit(key='ip', method='GET', rate='10/s')(check_thread), name="check_thread"),
    path("create-thread/", ratelimit(key='ip', method='GET', rate='10/s')(create_thread_from_discord), name="create_thread_from_discord"),

    path("operator/<str:operator_slug>/vehicles/<int:vehicle_id>/archived-dates/", ratelimit(key='ip', method='GET', rate='10/s')(vehicle_archived_dates_json), name="vehicle_archived_dates_api"),

    path("trips/", ratelimit(key='ip', method='GET', rate='10/s')(TripListView.as_view()), name="trip-list"),
    #path("trips/update_positions/", ratelimit(key='ip', method='POST', rate='2/m')(simulate_positions_view), name="update-trip-positions"),
    path("trips/create/", ratelimit(key='ip', method='GET', rate='5/m')(StartNewTripView), name="create-trip"),
    path("trips/current_vehicle_trips/", ratelimit(key='ip', method='GET', rate='10/s')(current_vehicle_trips.as_view()), name="current-vehicle-trips"),
    #path("trips/simulated_positions/", ratelimit(key='ip', method='GET', rate='10/s')(VehiclePositionAPIView.as_view()), name="estimated-positions"),
    path("trips/simulated_positions/", ratelimit(key='ip', method='GET', rate='10/s')(trackingAPIView.as_view()), name="simulated-positions"),
    path("trips/vehicle/<int:vehicle_id>/simulate/", ratelimit(key='ip', method='POST', rate='30/m')(push_sim_position), name="push_sim_position"),
    path("trips/<int:trip_id>/tracking/", ratelimit(key='ip', method='POST', rate='30/m')(push_trip_position), name="push-trip-position"),
    path("trips/<int:trip_id>/", ratelimit(key='ip', method='GET', rate='10/s')(TripDetailView.as_view()), name="trip-detail"),

    path("tracking/", ratelimit(key='ip', method='GET', rate='10/s')(TrackingListView.as_view()), name="tracking-list"),
    path("tracking/create/", ratelimit(key='ip', method='GET', rate='5/m')(create_tracking), name="create-tracking-template"),
    path("tracking/<int:tracking_id>/", ratelimit(key='ip', method='GET', rate='10/s')(TrackingDetailView.as_view()), name="tracking-detail"),
    path("tracking/vehicle/<int:vehicle_id>/", ratelimit(key='ip', method='GET', rate='10/s')(TrackingByVehicleView.as_view()), name="tracking-by-vehicle"),

    path('route_trip_eta/', ratelimit(key='ip', method='GET', rate='10/s')(RouteTripETAView.as_view()), name='route_trip_eta'),

    path('user/operators/', ratelimit(key='ip', method='GET', rate='10/s')(get_user_operators), name='get_user_operators'),
    path("user/operator/<int:opID>/fleet/", ratelimit(key='ip', method='GET', rate='10/s')(operator_fleet_view)),
    path("user/operator/<int:opID>/routes/", ratelimit(key='ip', method='GET', rate='10/s')(operator_routes_view)),
    path("user/add_badge/", ratelimit(key='ip', method='GET', rate='10/s')(give_badge)),

    path("all-available-badges/", ratelimit(key='ip', method='GET', rate='10/s')(get_all_available_badges), name="get_all_available_badges"),

    path("tickets/", ratelimit(key='ip', method='GET', rate='10/s')(ticket_list_api), name="ticket_list_api"),

    path("", ratelimit(key='ip', method='GET', rate='100/s')(api_root), name='home'),

    path("key-auth/create-ticket/", ratelimit(key='ip', method='GET', rate='5/m')(create_ticket_api_key_auth), name="create_ticket_api_key_auth"),
    path("key-auth/<int:ticket_id>/messages/", ratelimit(key='ip', method='GET', rate='5/s')(ticket_messages_api_key_auth), name="ticket_messages_api_key_auth"),
    path("<int:ticket_id>/messages/", ratelimit(key='ip', method='GET', rate='5/s')(ticket_messages_api), name="ticket_messages_api"),
]
