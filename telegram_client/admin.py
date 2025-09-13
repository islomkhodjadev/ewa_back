# telegram_client/admin.py
from django.contrib import admin
from unfold.admin import ModelAdmin, StackedInline

from .models import BotClient, BotClientSession


# ---------- Inlines ----------
class BotClientSessionInline(StackedInline):
    model = BotClientSession
    extra = 0
    can_delete = True
    fk_name = "client"
    fields = ("current_button", "updated_at")
    readonly_fields = ("updated_at",)
    show_change_link = True


# ---------- Actions ----------
@admin.action(description="✅ Отметить как проверенных")
def mark_verified(modeladmin, request, queryset):
    queryset.update(is_verified=True)


@admin.action(description="❌ Снять проверку")
def unmark_verified(modeladmin, request, queryset):
    queryset.update(is_verified=False)


@admin.action(description="🔐 Отметить как вошедших")
def mark_logined(modeladmin, request, queryset):
    queryset.update(is_logined=True)


@admin.action(description="🚪 Отметить как вышедших")
def unmark_logined(modeladmin, request, queryset):
    queryset.update(is_logined=False)


# ---------- Admins ----------
@admin.register(BotClient)
class BotClientAdmin(ModelAdmin):
    list_display = (
        "id",
        "is_verified",
        "is_logined",
        "first_name",
        "last_name",
        "username",
        "phone_number",
        "chat_id",
        "last_active",
        "created_at",
    )
    list_display_links = ("id", "first_name", "last_name")
    list_filter = (
        "is_verified",
        "is_logined",
        ("created_at", admin.DateFieldListFilter),
        ("last_active", admin.DateFieldListFilter),
    )
    search_fields = (
        "first_name",
        "last_name",
        "username",
        "phone_number",
        "chat_id",
    )
    ordering = ("-last_active",)
    date_hierarchy = "last_active"
    list_select_related = ()
    readonly_fields = ("created_at", "last_active")
    inlines = [BotClientSessionInline]
    actions = (mark_verified, unmark_verified, mark_logined, unmark_logined)

    fieldsets = (
        (
            "Статусы",
            {
                "fields": ("is_verified", "is_logined"),
            },
        ),
        (
            "Идентификаторы",
            {
                "fields": ("chat_id",),
            },
        ),
        (
            "Профиль",
            {
                "fields": ("first_name", "last_name", "username", "phone_number"),
            },
        ),
        (
            "Время",
            {
                "fields": ("created_at", "last_active"),
            },
        ),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Нет внешних связей, но оставим шаблон для расширения
        return qs


@admin.register(BotClientSession)
class BotClientSessionAdmin(ModelAdmin):
    list_display = ("id", "client", "current_button", "updated_at")
    list_select_related = ("client", "current_button")
    search_fields = (
        "client__first_name",
        "client__last_name",
        "client__username",
        "client__phone_number",
        "client__chat_id",
        "current_button__title",
    )
    list_filter = (("updated_at", admin.DateFieldListFilter),)
    readonly_fields = ("updated_at",)
    fieldsets = (
        (
            None,
            {
                "fields": ("client", "current_button", "updated_at"),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("client", "current_button")
