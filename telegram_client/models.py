from django.db import models
from django.utils import timezone
from telegram.models import ButtonTree


class BotClient(models.Model):
    is_verified = models.BooleanField(default=False, verbose_name="✅ Проверен")
    is_logined = models.BooleanField(default=False, verbose_name="✅ логин")
    chat_id = models.BigIntegerField(
        verbose_name="💬 ID чата", db_index=True, unique=True
    )
    first_name = models.CharField(
        max_length=100, verbose_name="🧑 Имя", null=True, blank=True
    )
    last_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="👨‍👩‍👦 Фамилия"
    )

    client_id = models.CharField(max_length=100, default="not set")
    phone_number = models.CharField(max_length=30, null=True, blank=True)
    username = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="📱 Имя пользователя Telegram",
    )

    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="🕰 Время регистрации"
    )

    last_active = models.DateTimeField(
        auto_now=True, verbose_name="⏳ Последняя активность"
    )

    class Meta:
        verbose_name = "🤖 Клиент бота"
        verbose_name_plural = "🤖 Клиенты бота"
        ordering = ["-last_active"]

    def __str__(self):
        return f"{self.first_name} {self.last_name or ''} ({self.chat_id})"

    async def aupdate_last_active(self):
        """Обновить поле последней активности."""
        self.last_active = timezone.now()
        await self.asave(update_fields=["last_active"])

    async def aupdate_verified(self, verified: bool = True):
        """Обновить статус верификации."""
        self.is_verified = verified
        await self.asave(update_fields=["is_verified"])

    async def aupdate_fields(self, **kwargs):
        """
        Универсальный асинхронный апдейтер.
        Пример: await client.aupdate_fields(first_name="Новый", username="newuser")
        """
        for field, value in kwargs.items():
            if hasattr(self, field):
                setattr(self, field, value)
        await self.asave(update_fields=list(kwargs.keys()))


class BotClientSession(models.Model):
    client = models.OneToOneField(
        BotClient,
        on_delete=models.CASCADE,
        related_name="session",
        verbose_name="👤 Клиент",
        unique=True,
    )
    current_button = models.ForeignKey(
        ButtonTree,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions",
        verbose_name="🔘 Текущая кнопка",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="⏳ Обновлено")

    class Meta:
        verbose_name = "📌 Сессия клиента"
        verbose_name_plural = "📌 Сессии клиентов"

    def __str__(self):
        return f"Сессия {self.client} → {self.current_button or 'нет кнопки'}"
