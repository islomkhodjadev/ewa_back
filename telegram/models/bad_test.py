# --- models/bad_test.py ---
from django.db import models


class BadTestQuestion(models.Model):
    question_text = models.TextField()
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Вопрос BAD теста"
        verbose_name_plural = "Вопросы BAD теста"
        ordering = ["order"]


class BadTestAnswer(models.Model):
    question = models.ForeignKey(
        BadTestQuestion, on_delete=models.CASCADE, related_name="answers"
    )
    answer_text = models.TextField()
    points_beauty = models.IntegerField(default=0)
    points_weight_loss = models.IntegerField(default=0)
    points_energy = models.IntegerField(default=0)
    points_brain = models.IntegerField(default=0)
    points_edema = models.IntegerField(default=0)
    points_stress = models.IntegerField(default=0)
    points_joints = models.IntegerField(default=0)
    order = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Ответ BAD теста"
        verbose_name_plural = "Ответы BAD теста"
        ordering = ["question__order", "order"]


class BadTestProduct(models.Model):
    CATEGORY_CHOICES = [
        ("beauty", "Красота"),
        ("weight_loss", "Похудение"),
        ("energy", "Энергия"),
        ("brain", "Мозг"),
        ("edema", "Отеки"),
        ("stress", "Стресс"),
        ("joints", "Суставы"),
    ]

    PRIORITY_CHOICES = [
        ("primary", "Основной"),
        ("secondary", "Вторичный"),
    ]

    name = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default="primary"
    )
    description = models.TextField(blank=True)
    dosage = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Продукт БАД"
        verbose_name_plural = "Продукты БАД"


class BadTestSession(models.Model):
    client = models.ForeignKey("telegram_client.BotClient", on_delete=models.CASCADE)
    current_question = models.ForeignKey(
        BadTestQuestion, on_delete=models.SET_NULL, null=True, blank=True
    )
    answers_data = models.JSONField(default=dict)  # Store answers and scores
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Сессия BAD теста"
        verbose_name_plural = "Сессии BAD теста"
        unique_together = ["client", "is_completed"]
