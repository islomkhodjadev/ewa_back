from django.urls import path, re_path
from .consumers import NotificationsConsumer

websocket_urlpatterns = [
    re_path(r"^ws/notifications/(?P<user_id>\d+)/$", NotificationsConsumer.as_asgi()),
]
