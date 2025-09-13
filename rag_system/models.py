from django.db import models
from pgvector.django import VectorField


class Embedding(models.Model):
    raw_text = models.TextField(verbose_name="Исходный текст")
    embedded_vector = VectorField(
        dimensions=768,
        null=True,
        blank=True,
        verbose_name="Векторное представление",
    )

    class Meta:
        verbose_name = "Встраивание"
        verbose_name_plural = "Встраивания"

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
