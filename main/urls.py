from django.urls import path
from main.views import *

urlpatterns = [
    path('', index),
    path('set-theme/', set_theme, name='set_theme'),
    path('region/<str:region_code>/', region_view, name='region_view'),
    path('search/', search, name='search'),
    path('rules/', rules, name='rules'),
    path('report/', report_view, name='report'),
    path('report/thank-you/', report_thank_you_view, name='report_thank_you'),
    path('data/', data, name='data'),
    path('create/livery/', create_livery, name='create_livery'),
    path('create/vehicle/', create_vehicle, name='create_vehicle'),
    path("for_sale/", for_sale, name='for_sale'),
    
    path("map/", live_map, name='map'),
    path("map/vehicle/<int:vehicle_id>/", live_vehicle_map, name='map_vehicle'),
    path("map/route/<int:route_id>/", live_route_map, name='map_route'),

    path("status/", status, name='stats'),
    path("site-updates/", site_updates, name='site_updates'),
    path('create/livery/progress/<int:livery_id>/', create_livery_progress, name='create_livery_progress'),
    path('queue/', queue_page, name='queue'),
    path('import-data/', import_mbt_data, name='import_mbt_data'),
    path('import-status/<uuid:job_id>/', import_status, name='import_status'),
]
