from django.urls import path
from integrations.websocket.consumer import HmiConsumer

websocket_urlpatterns = [
    path("ws/hmi/", HmiConsumer.as_asgi()),
]
