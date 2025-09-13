# admin.py
from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from rag_system.models import Embedding, EmbeddingData
from rag_system.utils.embeddings import get_embedding


class EmbeddingDataInline(TabularInline):
    model = EmbeddingData
    extra = 1
    fields = ("file",)


@admin.register(Embedding)
class EmbeddingAdmin(ModelAdmin):
    list_display = ("short_text", "has_embedding")
    search_fields = ("raw_text",)

    # 1) Полностью исключаем оригинальное поле из формы
    exclude = ("embedded_vector",)

    # 2) Показываем вместо него безопасное readonly-превью
    readonly_fields = ("embedding_preview",)

    # 3) Явно фиксируем порядок/состав полей, чтобы Unfold/Django ничего не «добавил»
    fields = (
        "raw_text",
        "embedding_preview",
    )  # добавьте сюда нужные другие поля модели

    inlines = (EmbeddingDataInline,)

    @admin.display(description="Текст (начало)")
    def short_text(self, obj):
        return (obj.raw_text or "")[:50]

    @admin.display(boolean=True, description="Есть вектор?")
    def has_embedding(self, obj):
        v = getattr(obj, "embedded_vector", None)
        try:
            return v is not None and len(v) > 0
        except TypeError:
            return v is not None

    @admin.display(description="Embedding (preview)")
    def embedding_preview(self, obj):
        v = getattr(obj, "embedded_vector", None)
        if v is None:
            return ""
        try:
            v = v.tolist()
        except AttributeError:
            pass
        if isinstance(v, (list, tuple)):
            head = ", ".join(f"{x:.4f}" for x in v[:8])
            tail = " …" if len(v) > 8 else ""
            return format_html(
                "<code>[{}{}]</code><br><small>len={}</small>", head, tail, len(v)
            )
        return format_html("<code>{}</code>", str(v)[:500])

    def save_model(self, request, obj, form, change):
        if getattr(obj, "embedded_vector", None) is None and obj.raw_text:
            vec = get_embedding(obj.raw_text)
            try:
                vec = vec.tolist()
            except AttributeError:
                pass
            obj.embedded_vector = vec
        super().save_model(request, obj, form, change)
