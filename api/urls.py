from django.urls import path
from fleet.views import *
from routes.views import *

urlpatterns = [
    path('liveries/', liveriesListView.as_view(), name='liveries-list'),
    path('liveries/<int:pk>/', liveriesDetailView.as_view(), name='liveries-detail'),
    path('type/', typeListView.as_view(), name='type-list'),
    path('type/<int:pk>/', typeDetailView.as_view(), name='type-detail'),
    path('routes/<int:pk>/stops/', routeStops.as_view(), name='route-stops'),
]
