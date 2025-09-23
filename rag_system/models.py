from django.db import models
from pgvector.django import VectorField


class Embedding(models.Model):
    raw_text = models.TextField(verbose_name="Исходный текст")
    embedded_vector = VectorField(
        dimensions=768,
        null=True,
        blank=True,
        verbose_name="Векторный эмбеддинг",
    )

    class Meta:
        verbose_name = "Эмбеддинг"
        verbose_name_plural = "Эмбеддинг"

    def __str__(self):
        return self.raw_text[:50]  # показываем первые 50 символов текста


class EmbeddingData(models.Model):
    embedding = models.ForeignKey(
        Embedding,
        on_delete=models.CASCADE,
        related_name="data",
        verbose_name="Встраивание",
    )
    file = models.FileField(
        upload_to="data/",
        null=True,
        blank=True,
        verbose_name="Файл",
    )

    class Meta:
        verbose_name = "Данные встраивания"
        verbose_name_plural = "Данные встраиваний"

    def __str__(self):
        return f"Файл для {self.embedding}"


class Utils(models.Model):
    base_rules = models.TextField(verbose_name="Основные правила")
    base_information = models.TextField(verbose_name="Базовая информация")
    gpt_model = models.CharField(max_length=50, verbose_name="GPT-модель")
    is_active = models.BooleanField(default=False, verbose_name="Активна")
    last_message_count = models.PositiveIntegerField(
        default=10, verbose_name="Количество последних сообщений"
    )
    choose_embedding_rule = models.TextField(verbose_name="Правило выбора эмбеддинга")

    class Meta:
        verbose_name = "Утилита"
        verbose_name_plural = "Утилиты"

    def __str__(self):
        return f"Утилита: {self.gpt_model} ({'активна' if self.is_active else 'не активна'})"

    def save(self, *args, **kwargs):
        # если эта запись активна → все остальные станут неактивными
        if self.is_active:
            Utils.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


from enum import Enum


class ChatTypes(Enum):
    SKYNET = "Тренажер"
    CHAT = "Чат"


class Roles(models.Model):
    behaviour = models.TextField(verbose_name="Поведение")
    name = models.CharField(unique=True, verbose_name="Название")
    summarize_behaviour = models.TextField(
        verbose_name="Поведение итоги",
        default="Here you should summarize based on the history and your behaviour",
    )

    class Meta:
        verbose_name = "Роль"
        verbose_name_plural = "Роли"

    def __str__(self):
        return self.name
