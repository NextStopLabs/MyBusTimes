# mybustimes/asgi.py
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mybustimes.settings")
django.setup()  # settings are ready here

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from messaging.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
