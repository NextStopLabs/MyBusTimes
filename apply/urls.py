from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("apply/<int:position_id>/", views.apply_position, name="apply_position"),
]
