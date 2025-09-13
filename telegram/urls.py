from django.urls import path
from telegram.views import webhook_async_view


urlpatterns = [path("webhook/<str:bot_id>/updates/", webhook_async_view)]
