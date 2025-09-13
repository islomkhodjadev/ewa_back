import asyncio
import aiogram
import logging

logger = logging.getLogger(__name__)


from django.core.management.base import BaseCommand

from django.conf import settings

bot = aiogram.Bot(token=settings.BOT_TOKEN)


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.set_webhook())

    async def set_webhook(self):
        webhook_info = await bot.get_webhook_info()
        logger.info(f"Current webhook info {webhook_info}")

        if webhook_info.url != settings.BOT_WEBHOOK_URL:
            await bot.set_webhook(settings.BOT_WEBHOOK_URL)
            logger.info(f"Webhook set to {settings.BOT_WEBHOOK_URL}")
        else:
            logger.info("Webhook already set to the desired value")

        await bot.session.close()
