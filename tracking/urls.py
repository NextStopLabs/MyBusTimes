from django.contrib import admin
from django.urls import path, include
from .views import *
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    #path('game-tracking/update-tracking/', update_tracking.as_view(), name='update-tracking'),
    path('tracking/update/<int:tracking_id>/', update_tracking, name='update_tracking'),
    #path('game-tracking/create-tracking/', create_tracking.as_view(), name='create-tracking'),
    path('start/', create_tracking_template, name='create-tracking-template'),
    path('update/<tracking_id>/', update_tracking_template, name='update-tracking-template'),
    path('end/<tracking_id>/', end_trip, name='end_trip'),
    path('game-tracking/data/history', map_view_history.as_view(), name='map-view'),
    path('game-tracking/data/', map_view.as_view(), name='map-view'),
    path('game-tracking/data/history/<tracking_id>/', map_view_history.as_view(), name='map-view'),
    path('game-tracking/data/<tracking_id>/', map_view.as_view(), name='map-view'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

