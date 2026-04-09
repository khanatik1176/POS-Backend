from django.urls import re_path
from .consumers import OrderUpdatesConsumer

websocket_urlpatterns = [
    re_path(r'^ws/orders/$', OrderUpdatesConsumer.as_asgi()),
]
