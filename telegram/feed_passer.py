from django.conf import settings
from telegram.instance import instance_main


class BotFeedPasser:
    @classmethod
    async def feed_pass(cls, token: str, update: dict):
        await instance_main.feed_update(token=token, update=update)
