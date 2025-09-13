from rest_framework import serializers
from telegram_client.models import BotClient


class BotClientSerializers(serializers.ModelSerializer):

    class Meta:
        model = BotClient
        fields = (
            "id",
            "is_verified",
            "is_logined",
            "chat_id",
            "first_name",
            "last_name",
            "chat_id",
            "phone_number",
            "username",
        )
