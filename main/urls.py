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
    path("proxy/valhalla/<str:type>/", valhalla_proxy),
    path("for_sale/", for_sale, name='for_sale'),
    path("map/", live_map, name='map'),
    path("status/", status, name='stats'),
    path("site-updates/", site_updates, name='site_updates'),
    path('create/livery/progress/<int:livery_id>/', create_livery_progress, name='create_livery_progress'),
]
