from rest_framework import serializers
from telegram_client.serializers import BotClientSerializers
from miniapp.models import ChatSession, Message
from rag_system.serializers import EmbeddingSerializer
from rag_system.serializers import RolesSerializer
from rag_system.utils.get_buttons import get_buttons


class MessageSerializer(serializers.ModelSerializer):
    embedding = EmbeddingSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ("id", "message", "embedding", "owner", "created_at")


class ChatSessionSerializer(serializers.ModelSerializer):

    bot_client = BotClientSerializers(read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    current_role = RolesSerializer(read_only=True)
    buttons = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ChatSession
        fields = ("id", "bot_client", "messages", "mode", "current_role", "buttons")

    def get_buttons(self, obj):
        buttons = get_buttons(obj)
        if "buttons" in buttons:
            return buttons["buttons"]
        elif "roles" in buttons:
            return buttons["roles"]
        return None
