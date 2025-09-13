from rest_framework import serializers
from telegram_client.serializers import BotClientSerializers
from miniapp.models import ChatSession, Message
from rag_system.serializers import EmbeddingSerializer


class MessageSerializer(serializers.ModelSerializer):
    embedding = EmbeddingSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ("id", "message", "embedding", "owner", "created_at")


class ChatSessionSerializer(serializers.ModelSerializer):

    bot_client = BotClientSerializers(read_only=True)
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatSession
        fields = ("id", "bot_client", "messages")
