from django.urls import path
from fleet.views import *

urlpatterns = [
    #path('', index),
    path('create/', create_operator, name='create-operator'),
    path('<str:operator_name>/', operator, name='operator'),
    path('<str:operator_name>/edit/', operator_edit, name='edit-operator'),
    path('<str:operator_name>/route/<int:route_id>/', route_detail, name='route_detail'),
    path('<str:operator_name>/route/<int:route_id>/map/', route_map, name='route_map'),
    path('<str:operator_name>/route/<int:route_id>/edit/', route_edit, name='edit-route'),
    path('<str:operator_name>/route/<int:route_id>/stops/add/<str:direction>/', route_add_stops, name='add-stops'),
    path('<str:operator_name>/route/<int:route_id>/stops/edit/<str:direction>/', route_edit_stops, name='edit-stops'),
    path('<str:operator_name>/route/<int:route_id>/timetable/add/<str:direction>', route_timetable_add, name='add-timetable'),
    path('<str:operator_name>/route/<int:route_id>/timetable/import/<str:direction>', route_timetable_import, name='import-timetable'),
    path('<str:operator_name>/route/<int:route_id>/timetable/edit/<int:timetable_id>/', route_timetable_edit, name='edit-timetable'),
    path('<str:operator_name>/route/<int:route_id>/timetable/options/', route_timetable_options, name='timetable-options'),
    path('<str:operator_name>/route/<int:route_id>/timetable/delete/<int:timetable_id>/', route_timetable_delete, name='delete-timetable'),
    path('<str:operator_name>/vehicles/', vehicles, name='vehicle_detail'),
    path('<str:operator_name>/vehicles/add-bus/', vehicle_add, name='add_vehicles'),
    path('<str:operator_name>/vehicles/<int:vehicle_id>/delete/', vehicle_delete, name='vehicle_delete'),
    path('<str:operator_name>/add-route/', route_add, name='add_route'),
    path('<str:operator_name>/vehicles/<int:vehicle_id>/', vehicle_detail, name='vehicle_detail'),
    path('<str:operator_name>/vehicles/<int:vehicle_id>/list_for_sale/', vehicle_sell, name='vehicle_sell'),
    path('<str:operator_name>/vehicle/edit/<int:vehicle_id>/', vehicle_edit, name='vehicle_edit'),
]
