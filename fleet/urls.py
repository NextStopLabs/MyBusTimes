from django.urls import path
from fleet.views import *

urlpatterns = [
    path('history/', fleet_history, name='fleet_history'),

    # Operator types
    path('types/', operator_types, name='operator-types'),
    path('types/<str:operator_type_name>/', operator_type_detail, name='operator-type-detail'),
    path('games/<str:operator_game_name>/', operator_game_detail, name='operator-game-detail'),
    path('create-type/', operator_type_add, name='add-operator-type'),

    # Operator management
    path('create/', create_operator, name='create-operator'),
    path('<str:operator_slug>/', operator, name='operator'),
    path('<str:operator_slug>/edit/', operator_edit, name='edit-operator'),
    path('<str:operator_slug>/delete/', operator_delete, name='delete_operator'),
    path('<str:operator_slug>/reset/', operator_reset, name='reset_operator'),
    # Tickets
    path('<str:operator_slug>/tickets/', operator_tickets, name='operator_tickets'),
    path('<str:operator_slug>/tickets/add/', operator_ticket_add, name='add_operator_ticket'),
    path('<str:operator_slug>/tickets/edit/<int:ticket_id>/', operator_ticket_edit, name='edit_operator_ticket'),
    path('<str:operator_slug>/tickets/delete/<int:ticket_id>/', operator_ticket_delete, name='delete_operator_ticket'),
    path('<str:operator_slug>/tickets/<str:zone_name>/', operator_tickets_details, name='operator_tickets_details'),

    # Duties
    path('<str:operator_slug>/duties/', duties, name='operator-duties'),
    path('<str:operator_slug>/duties/add/', duty_add, name='add-duty'),
    path('<str:operator_slug>/duties/add/trips/<int:duty_id>/', duty_add_trip, name='add-duty-trips'),
    path('<str:operator_slug>/duties/delete/<int:duty_id>/', duty_delete, name='delete-duty'),
    path('<str:operator_slug>/duties/edit/<int:duty_id>/', duty_edit, name='edit-duty'),
    path('<str:operator_slug>/duties/edit/<int:duty_id>/trips/', duty_edit_trips, name='edit-duty-trips'),
    path('<str:operator_slug>/duties/<int:duty_id>/', duty_detail, name='duty_detail'),

    # Running boards
    path('<str:operator_slug>/running-boards/', duties, name='operator-duties'),
    path('<str:operator_slug>/running-boards/add/', duty_add, name='add-running-board'),
    path('<str:operator_slug>/running-boards/add/trips/<int:duty_id>/', duty_add_trip, name='add-duty-trips'),
    path('<str:operator_slug>/running-boards/delete/<int:duty_id>/', duty_delete, name='delete-duty'),
    path('<str:operator_slug>/running-boards/edit/<int:duty_id>/', duty_edit, name='edit-duty'),
    path('<str:operator_slug>/running-boards/edit/<int:duty_id>/trips/', duty_edit_trips, name='edit-duty-trips'),
    path('<str:operator_slug>/running-boards/<int:duty_id>/', duty_detail, name='duty_detail'),

    # Duty printout
    path('<str:operator_slug>/printout/generate-pdf/<int:duty_id>/', generate_pdf, name='generate_pdf'),

    # Route management
    path('<str:operator_slug>/add-route/', route_add, name='add_route'),
    path('<str:operator_slug>/route/<int:route_id>/', route_detail, name='route_detail'),
    path('<str:operator_slug>/route/<int:route_id>/edit/', route_edit, name='edit-route'),
    path('<str:operator_slug>/route/<int:route_id>/delete/', route_delete, name='delete-route'),
    path("<str:operator_slug>/route/<int:route_id>/vehicles/", route_vehicles, name="route_vehicles"),
    path('<str:operator_slug>/routes/dedupe', deduplicate_operator_routes, name='deduplicate_routes'),

    # Route Updates
    path('<str:operator_slug>/route/<int:route_id>/updates/options/', route_updates_options, name='route_updates_options'),
    path('<str:operator_slug>/route/<int:route_id>/updates/add/', route_update_add, name='add_route_update'),
    path('<str:operator_slug>/route/<int:route_id>/updates/edit/<int:update_id>/', route_update_edit, name='edit_route_update'),
    path('<str:operator_slug>/route/<int:route_id>/updates/delete/<int:update_id>/', route_update_delete, name='delete_route_update'),

    # Route stops
    path('<str:operator_slug>/route/<int:route_id>/stops/add/<str:direction>/', route_add_stops, name='add-stops'),
    path('<str:operator_slug>/route/<int:route_id>/stops/add/<str:direction>/stop-names-only/', add_stop_names_only, name='add-stop-names-only'),
    path('<str:operator_slug>/route/<int:route_id>/stops/edit/<str:direction>/', route_edit_stops, name='edit-stops'),
    path('<str:operator_slug>/route/<int:route_id>/stops/edit/<str:direction>/stop-names-only/', edit_stop_names_only, name='edit-stop-names-only'),

    # Route timetables
    path('<str:operator_slug>/route/<int:route_id>/timetable/add/<str:direction>', route_timetable_add, name='add-timetable'),
    path('<str:operator_slug>/route/<int:route_id>/timetable/import/<str:direction>', route_timetable_import, name='import-timetable'),
    path('<str:operator_slug>/route/<int:route_id>/timetable/edit/<int:timetable_id>/', route_timetable_edit, name='edit-timetable'),
    path('<str:operator_slug>/route/<int:route_id>/timetable/options/', route_timetable_options, name='timetable-options'),
    path('<str:operator_slug>/route/<int:route_id>/timetable/delete/<int:timetable_id>/', route_timetable_delete, name='delete-timetable'),

    # Vehicles
    path('<str:operator_slug>/vehicles/', vehicles, name='vehicles'),
    path('<str:operator_slug>/vehicles/add-bus/', vehicle_add, name='add_vehicles'),
    path('<str:operator_slug>/vehicles/mass-add-bus/', vehicle_mass_add, name='mass_add_vehicles'),
    path('<str:operator_slug>/vehicles/mass-edit-bus/', vehicle_mass_edit, name='mass_edit_vehicles'),
    path('<str:operator_slug>/vehicles/select-mass-edit-bus/', vehicle_select_mass_edit, name='mass_edit_vehicle_select'),
    path('<str:operator_slug>/vehicles/<int:vehicle_id>/', vehicle_detail, name='vehicle_detail'),
    path('<str:operator_slug>/vehicles/<int:vehicle_id>/delete/', vehicle_delete, name='vehicle_delete'),
    path('<str:operator_slug>/vehicles/<int:vehicle_id>/log_trip/', log_trip, name='log_trip'),
    path('<str:operator_slug>/vehicles/<int:vehicle_id>/list_for_sale/', vehicle_sell, name='vehicle_sell'),
    path('<str:operator_slug>/vehicle/edit/<int:vehicle_id>/', vehicle_edit, name='vehicle_edit'),
    path('<str:operator_slug>/vehicles/dedupe', deduplicate_operator_fleet, name='deduplicate_fleet'),
    
    # Trips
    path('<str:operator_slug>/vehicles/<int:vehicle_id>/trips/manage/', vehicles_trip_manage, name='vehicles_trip_manage'),
    path('<str:operator_slug>/vehicles/<int:vehicle_id>/trips/<int:trip_id>/miss/', vehicles_trip_miss, name='vehicles_trip_miss'),
    path('<str:operator_slug>/vehicles/<int:vehicle_id>/trips/<int:trip_id>/edit/', vehicles_trip_edit, name='vehicles_trip_edit'),
    path('<str:operator_slug>/vehicles/<int:vehicle_id>/trips/<int:trip_id>/delete/', vehicles_trip_delete, name='vehicles_trip_delete'),
    path('<str:operator_slug>/vehicles/<int:vehicle_id>/trips/remove_other_trips/', remove_other_trips, name='remove_other_trips'),
    path('<str:operator_slug>/vehicles/<int:vehicle_id>/trips/remove_all_trips/', remove_all_trips, name='remove_all_trips'),


    # Vehicle for sale/status/images
    path('for_sale/status/<int:vehicle_id>/', vehicle_status_preview, name='vehicle_status_preview'),
    path('vehicle_image/<int:vehicle_id>/', vehicle_card_image, name='vehicle_card_image'),

    # Updates
    path('<str:operator_slug>/updates/', operator_updates, name='operator_updates'),
    path('<str:operator_slug>/updates/add/', operator_update_add, name='add_operator_update'),
    path('<str:operator_slug>/updates/edit/<int:update_id>/', operator_update_edit, name='edit_operator_update'),
    path('<str:operator_slug>/updates/delete/<int:update_id>/', operator_update_delete, name='delete_operator_update'),

    # Helpers
    path('<str:operator_slug>/helpers/', operator_helpers, name='operator_helpers'),
    path('<str:operator_slug>/helpers/add/', operator_helper_add, name='operator_helper_add'),
    path('<str:operator_slug>/helpers/edit/<int:helper_id>/', operator_helper_edit, name='operator_helper_edit'),
    path('<str:operator_slug>/helpers/remove/<int:helper_id>/', operator_helper_delete, name='operator_helper_delete'),

    # Trips
    path('<str:operator_slug>/vehicles/mass-log-trips', mass_log_trips, name='operator_mass_log_trips'),
]
