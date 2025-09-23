# models.py
from django.db import models
from telegram_client.models import BotClient
from rag_system.models import Embedding
from channels.db import database_sync_to_async
from django.db.models import F, Case, When, Value
from rag_system.models import Roles


class ChatSession(models.Model):
    SKYNET = "skynet"
    CHAT = "chat"
    mode_types = ((CHAT, "chat"), (SKYNET, "skynet"))

    bot_client = models.OneToOneField(
        BotClient, on_delete=models.CASCADE, related_name="chatsession", unique=True
    )

    mode = models.CharField(choices=mode_types, max_length=6, default=CHAT)
    current_role = models.ForeignKey(
        Roles, on_delete=models.SET_DEFAULT, default=None, null=True, blank=True
    )

    def __str__(self):
        return f"ChatSession #{self.pk} – {self.bot_client}"

    @database_sync_to_async
    def get_history_async(self, message_count: int):
        # Get the latest message_count message IDs
        latest_message_ids = self.messages.order_by("-id").values_list("id", flat=True)[
            :message_count
        ]

        # Get messages with these IDs in ascending order
        return list(
            self.messages.filter(id__in=latest_message_ids)
            .order_by("id")
            .annotate(role=F("owner"), content=F("message"))
            .values("role", "content")
        )

    def get_history(self, message_count: int):
        # First, find the most recent summarize_end message
        last_summarize_end = (
            self.messages.filter(summarize_end=True).order_by("-id").first()
        )

        if last_summarize_end:
            # If there's a summarize_end, get messages after that point
            messages_after_summarize = self.messages.filter(
                id__gt=last_summarize_end.id
            ).order_by("-id")[:message_count]
        else:
            # If no summarize_end, get the latest messages normally
            messages_after_summarize = self.messages.order_by("-id")[:message_count]

        # Get the IDs of these messages
        message_ids = messages_after_summarize.values_list("id", flat=True)

        # Get messages with these IDs in ascending order
        return list(
            self.messages.filter(id__in=message_ids)
            .order_by("id")
            .annotate(
                role=Case(
                    When(owner="user", then=Value("user")),
                    When(owner="system", then=Value("assistant")),
                    When(owner="ai", then=Value("assistant")),
                    When(owner="assistant", then=Value("assistant")),
                    default=Value("assistant"),
                    output_field=models.CharField(),
                ),
                content=F("message"),
            )
            .values("role", "content")
        )

    def get_last_summarization_history(self):

        last_summarize_start = (
            self.messages.filter(summarize_start=True).order_by("-id").first()
        )

        if not last_summarize_start:
            return []

        return (
            self.messages.filter(
                id__gt=last_summarize_start.id,  # End must be AFTER start
            )
            .order_by("id")
            .annotate(role=F("owner"), content=F("message"))
            .values("role", "content")
        )

    def get_last_summarization_history_v2(self):
        last_summarize_start = (
            self.messages.filter(summarize_start=True).order_by("-id").first()
        )

        if not last_summarize_start:
            return []

        return (
            self.messages.filter(
                id__gt=last_summarize_start.id,
            )
            .order_by("id")
            .annotate(
                role=Case(
                    When(owner="user", then=Value("user")),
                    When(owner="system", then=Value("assistant")),
                    When(owner="ai", then=Value("assistant")),
                    When(owner="assistant", then=Value("assistant")),
                    default=Value(
                        "assistant"
                    ),  # Default to assistant for any other owner
                    output_field=models.CharField(),
                ),
                content=F("message"),
            )
            .values("role", "content")
        )


class Message(models.Model):
    USER = "user"
    AI = "system"
    OWNER_CHOICES = (
        (USER, "user"),
        (AI, "system"),
    )

    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name="messages"  # plural
    )
    summarize_start = models.BooleanField(default=False)
    summarize_end = models.BooleanField(default=False)
    message = models.TextField()
    embedding = models.ForeignKey(
        Embedding, on_delete=models.SET_NULL, null=True, blank=True
    )
    owner = models.CharField(choices=OWNER_CHOICES, max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.owner}] {self.message[:40]}..."
