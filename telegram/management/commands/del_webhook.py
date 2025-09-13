import asyncio
import logging
import aiogram

from django.conf import settings

from django.core.management.base import BaseCommand

bot = aiogram.Bot(token=settings.BOT_TOKEN)


class Command(BaseCommand):

    help = "Clear old cache and old requests for the bot"

    def handle(self, *args, **kwargs):

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.del_webhook())

    async def del_webhook(self):
        webhook_info = await bot.get_webhook_info()
        logging.info(f"Current webhook info is {webhook_info}")
        if webhook_info.url:
            await bot.delete_webhook(drop_pending_updates=True)
            logging.info("Old webhook deleted")

        await bot.session.close()
