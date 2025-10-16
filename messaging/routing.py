from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^message/ws/chat/(?P<chat_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
]