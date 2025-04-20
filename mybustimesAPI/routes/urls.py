from django.urls import path
from . import views

urlpatterns = [
    # Routes
    path('routes/', views.routesListView.as_view(), name='route-list'),
    path('routes/<int:pk>/', views.routesDetailView.as_view(), name='route-detail'),

    # Stops
    path('stops/', views.stopListView.as_view(), name='stop-list'),
    path('stops/<int:pk>/', views.stopDetailView.as_view(), name='stop-detail'),

    # Day Types
    path('day-types/', views.dayTypeListView.as_view(), name='daytype-list'),

    # Timetable Entries
    path('timetable-entries/', views.timetableEntryListView.as_view(), name='timetableentry-list'),
    path('timetable-entries/<int:pk>/', views.timetableEntryDetailView.as_view(), name='timetableentry-detail'),

    # Custom timetable view
    # path('timetable/<str:route_id>/<str:day_type>/', views.timetableView.as_view(), name='timetable-by-route-and-day'),
]
