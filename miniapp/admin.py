# admin.py
from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import ChatSession, Message


class MessageInline(TabularInline):
    model = Message
    fields = ("owner", "message", "embedding", "created_at")
    readonly_fields = ("created_at",)
    extra = 0
    show_change_link = True


@admin.register(ChatSession)
class ChatSessionAdmin(ModelAdmin):
    list_display = ("id", "bot_client", "messages_count")
    search_fields = ("bot_client__id", "bot_client__name")
    autocomplete_fields = ("bot_client",)
    inlines = [MessageInline]

    def messages_count(self, obj):
        # use obj.message.count() if your related_name is singular
        return obj.messages.count()

    messages_count.short_description = "Messages"


@admin.register(Message)
class MessageAdmin(ModelAdmin):
    list_display = (
        "id",
        "session",
        "owner",
        "short_message",
        "embedding",
        "created_at",
    )
    list_filter = ("owner", "created_at")
    search_fields = ("message", "session__bot_client__name")
    autocomplete_fields = ("session", "embedding")
    readonly_fields = ("created_at",)
    list_select_related = ("session", "session__bot_client", "embedding")

    def short_message(self, obj):
        text = obj.message or ""
        return (text[:60] + "…") if len(text) > 60 else text

    short_message.short_description = "Message"
