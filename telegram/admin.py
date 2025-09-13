# telegram/admin.py
from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline, StackedInline

from .models import ButtonTree, AttachmentToButton, AttachmentData


# ---------- Inlines ----------
class AttachmentDataInline(TabularInline):
    model = AttachmentData
    extra = 0
    fields = ("source",)
    show_change_link = True


class AttachmentToButtonInline(StackedInline):
    model = AttachmentToButton
    extra = 0
    fk_name = "button"
    max_num = 1
    fields = ("source_type", "text")
    show_change_link = True


# ---------- Admins ----------
@admin.register(ButtonTree)
class ButtonTreeAdmin(ModelAdmin):
    list_display = (
        "id",
        "text",
        "parent",
        "children_count",
        "has_material",
        "is_root",
        "is_leaf",
    )
    list_filter = ("parent",)
    search_fields = ("text", "parent__text")
    ordering = ("parent__id", "id")
    inlines = [AttachmentToButtonInline]

    def children_count(self, obj):
        return obj.children.count()

    children_count.short_description = "Дочерних узлов"

    def has_material(self, obj):
        return hasattr(obj, "attachment")

    has_material.boolean = True
    has_material.short_description = "Есть материал"


@admin.register(AttachmentToButton)
class AttachmentToButtonAdmin(ModelAdmin):
    list_display = ("id", "button", "source_type", "data_count", "preview_text")
    list_select_related = ("button",)
    list_filter = ("source_type",)
    search_fields = ("button__text", "text")
    inlines = [AttachmentDataInline]

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
    search_fields = (
        "attachment__button__text",
        "attachment__text",
    )
    fields = ("attachment", "source")

    def ext(self, obj):
        import os

        return (os.path.splitext(obj.source.name)[1] or "").lower()

    ext.short_description = "Расширение"

    def source_name(self, obj):
        return obj.source.name

    source_name.short_description = "Файл"
