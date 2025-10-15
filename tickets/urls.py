from django.urls import path
from . import views

from django_ratelimit.decorators import ratelimit

urlpatterns = [
    path("", views.ticket_home, name="ticket_home"),
    path("create/", ratelimit(key='ip', method='GET', rate='1/s')(views.create_ticket), name="create_ticket"),
    path("<int:ticket_id>/", views.ticket_detail, name="ticket_detail"),  # detail view placeholder
    path("<int:ticket_id>/close/", views.close_ticket, name="ticket_close"),  # close ticket view
    path('banned/', views.ticket_banned, name='ticket_banned'),
]
