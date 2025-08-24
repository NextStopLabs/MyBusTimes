from django.urls import path
from . import views

urlpatterns = [
    path("", views.ticket_home, name="ticket_home"),
    path("create/", views.create_ticket, name="create_ticket"),
    path("<int:ticket_id>/", views.ticket_detail, name="ticket_detail"),  # detail view placeholder
    path("<int:ticket_id>/close/", views.close_ticket, name="ticket_close"),  # close ticket view
]
