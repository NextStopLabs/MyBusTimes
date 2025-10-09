from django.urls import path
from main.views import *
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', index),
    path("help/", resources, name="help"),
    path('ads.txt', ads_txt_view, name='ads-txt'),
    path('favicon.ico', favicon, name='favicon'),
    path('set-theme/', set_theme, name='set_theme'),
    path('region/<str:region_code>/', region_view, name='region_view'),
    path('search/', search, name='search'),
    path('rules/', rules, name='rules'),
    path("contact/", contact, name="contact"),
    path('report/', report_view, name='report'),
    path('report/thank-you/', report_thank_you_view, name='report_thank_you'),
    path('data/', data, name='data'),
    path('create/livery/', create_livery, name='create_livery'),
    path('create/vehicle/', create_vehicle, name='create_vehicle'),
    path('create/game/', create_game, name='create_game'),
    path("for_sale/", for_sale, name='for_sale'),
 
    path("hub/", community_hub, name="community_hub"),
    path("hub/all_images/", community_hub_images, name="community_hub_images"),

    path("map/", live_map, name='map'),
    path("map/simple/", live_map_simple, name='map_simple'),
    path("map/vehicle/<int:vehicle_id>/", live_vehicle_map, name='map_vehicle'),
    path("map/route/<int:route_id>/", live_route_map, name='map_route'),
    path("map/trip/<int:trip_id>/", trip_map, name='map_trip'),

    path("status/", status, name='stats'),
    path("site-updates/", site_updates, name='site_updates'),
    path("patch-notes/", patch_notes, name='patch_notes'),
    path('create/livery/progress/<int:livery_id>/', create_livery_progress, name='create_livery_progress'),
    path('queue/', queue_page, name='queue'),
    path('import-data/', import_mbt_data, name='import_mbt_data'),
    path('import-status/<uuid:job_id>/', import_status, name='import_status'),
    path('import-status/data/<uuid:job_id>/', import_status_data, name='import_status_data'),

    path("ticketer/", ticketer_down, name="ticketer_down"),

    #displays
    path('displays/', bus_displays_view, name='bus_displays'),
    path("displays/blind/", bus_blind_view, name="bus_blind"),
    path("displays/simple/blind/", simple_bus_blind_view, name="simple_bus_blind"),
    path("displays/available-drivers/", available_drivers_view, name="available_drivers"),
    path("displays/internal/", bus_internal_view, name="bus_internal"),

    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset_done.html'
    ), name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html'
    ), name='password_reset_confirm'),

    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'
    ), name='password_reset_complete'),
]

handler404 = 'main.views.custom_404'