from django.contrib import admin
from django.urls import path, include
from gameData.views import *
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', gameListView.as_view(), name='gameListView'),
    path('<str:game_name>/', RouteDataView.as_view(), name='get_route_data'),
    path('<str:game_name>/Dests', RouteDestsDataView.as_view(), name='get_route_data')
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)