# models.py
from django.db import models
from telegram_client.models import BotClient
from rag_system.models import Embedding


class ChatSession(models.Model):
    bot_client = models.OneToOneField(
        BotClient, on_delete=models.CASCADE, related_name="chatsession", unique=True
    )

    def __str__(self):
        return f"ChatSession #{self.pk} – {self.bot_client}"


class Message(models.Model):
    USER = "user"
    AI = "ai"
    OWNER_CHOICES = (
        (USER, "User"),
        (AI, "AI"),
    )

    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name="messages"  # plural
    )
    message = models.TextField()
    embedding = models.ForeignKey(
        Embedding, on_delete=models.SET_NULL, null=True, blank=True
    )
    owner = models.CharField(choices=OWNER_CHOICES, max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.owner}] {self.message[:40]}..."
