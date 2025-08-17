from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="messaging_home"),
    path("chat/<int:chat_id>/", views.chat_detail, name="chat_detail"),
    path("start-chat/", views.start_chat, name="start_chat"),
    path("send-file/", views.send_file, name="chat_send_file"),
]
