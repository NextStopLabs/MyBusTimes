from django.urls import path
from . import views
from routes.views import *

urlpatterns = [
    path('routes/', views.routesListView.as_view(), name='route-list'),
    path('routes/create/', views.routesCreateView.as_view(), name='route-create'),
    path('routes/<int:pk>/', views.routesDetailView.as_view(), name='route-detail'),
    path('day_type/', views.dayTypeListView.as_view(), name='day-type-list'),
    path('timetable/', views.timetableView.as_view(), name='timetable-view'),
    path('timetable/days/', views.timetableDaysView.as_view(), name='timetable-days'),
    path('stop/', views.stopRouteSearchView.as_view(), name='stop-route-search'),
    path('stop/times/', views.stopUpcomingTripsView.as_view(), name='stop-upcoming-trips'),
    path('duty/', views.dutyListView.as_view(), name='duty-list'),
    path('duty/<int:pk>/', views.dutyDetailView.as_view(), name='duty-detail'),
    path('transit_authorities/', views.transitAuthoritiesColourView.as_view(), name='transit-authorities-list'),
    path('transit_authorities/<str:code>/', views.transitAuthoritiesColourDetailView.as_view(), name='transit-authorities-detail'),
    path('', stop, name='stop'),
    #path('duty/trip/', views.dutyTripListView.as_view(), name='duty-trip-list'),
    #path('duty/trip/<int:pk>/', views.dutyTripDetailView.as_view(), name='duty-trip-detail'),
]
