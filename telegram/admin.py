# telegram/admin.py
from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from django.utils.html import format_html
import os

from .models import ButtonTree, AttachmentToButton, AttachmentData


# ---------- Inlines ----------
class AttachmentDataInline(TabularInline):
    model = AttachmentData
    extra = 1
    max_num = 10  # Limit maximum files if needed
    fields = ("source", "thumbnail", "file_preview")
    readonly_fields = ("file_preview",)

    def file_preview(self, obj):
        if obj and obj.source:
            filename = os.path.basename(obj.source.name)
            file_size = (
                self.format_file_size(obj.source.size) if obj.source.size else "Unknown"
            )
            return format_html(
                '<div style="font-size: 12px;">'
                "<div><strong>{}</strong></div>"
                '<div style="color: #666;">Size: {}</div>'
                "</div>",
                filename,
                file_size,
            )
        return "-"

    def format_file_size(self, size):
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    file_preview.short_description = "Текущий файл"


class AttachmentToButtonInline(StackedInline):
    model = AttachmentToButton
    extra = 0
    fk_name = "button"
    max_num = 1  # Only one attachment per button
    fields = ("source_type", "text")
    # This is the key - nest AttachmentData inside AttachmentToButton
    inlines = [AttachmentDataInline]

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        return fields


# ---------- Main Admin ----------
@admin.register(ButtonTree)
class ButtonTreeAdmin(ModelAdmin):
    list_display = (
        "id",
        "text",
        "parent",
        "children_count",
        "has_material",
        "files_count",
        "is_root",
        "is_leaf",
    )
    list_filter = ("parent",)
    search_fields = ("text", "parent__text")
    ordering = ("parent__id", "id")

    # This is the key - both levels nested under ButtonTree
    inlines = [AttachmentToButtonInline]

    fieldsets = (
        (
            "Основная информация",
            {"fields": ("text", "parent"), "description": "Основные настройки кнопки"},
        ),
    )

    def children_count(self, obj):
        count = obj.children.count()
        color = "green" if count > 0 else "gray"
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>', color, count
        )

    children_count.short_description = "👶 Дочерних узлов"

    def has_material(self, obj):
        return hasattr(obj, "attachment") and obj.attachment is not None

    has_material.boolean = True
    has_material.short_description = "📎 Есть материал"

    def files_count(self, obj):
        if hasattr(obj, "attachment") and obj.attachment:
            count = obj.attachment.data.count()
            color = "blue" if count > 0 else "gray"
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>', color, count
            )
        return format_html('<span style="color: gray;">0</span>')

    files_count.short_description = "📂 Файлов"

    def get_inline_instances(self, request, obj=None):
        """Ensure inlines work for both create and edit views"""
        return super().get_inline_instances(request, obj)


# Optional: Keep the separate admins for individual management
@admin.register(AttachmentToButton)
class AttachmentToButtonAdmin(ModelAdmin):
    list_display = ("id", "button", "source_type", "data_count", "preview_text")
    list_select_related = ("button",)
    list_filter = ("source_type",)
    search_fields = ("button__text", "text")
    inlines = [AttachmentDataInline]  # For when editing AttachmentToButton directly

    def data_count(self, obj):
        return obj.data.count()

    data_count.short_description = "Файлов"

    def preview_text(self, obj):
        return (obj.text[:50] + "…") if obj.text and len(obj.text) > 50 else obj.text

    preview_text.short_description = "Текст (превью)"


@admin.register(AttachmentData)
class AttachmentDataAdmin(ModelAdmin):
    list_display = ("id", "attachment", "ext", "source_name")
    list_select_related = ("attachment", "attachment__button")
    search_fields = ("attachment__button__text", "attachment__text")
    fields = ("attachment", "thumbnail", "source")

    def ext(self, obj):
        return (os.path.splitext(obj.source.name)[1] or "").lower()

    ext.short_description = "Расширение"

    def source_name(self, obj):
        return obj.source.name

    source_name.short_description = "Файл"
