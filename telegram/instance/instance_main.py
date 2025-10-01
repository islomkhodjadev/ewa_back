from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

from telegram.instance import handlers

webhook_dp = Dispatcher()


webhook_dp.include_routers(
    handlers.start_flow_router,
    handlers.profile_router,
    handlers.bad_test_router,
    handlers.tree_router,
)


async def feed_update(token: str, update: dict):
    bot = Bot(token=token)
    try:
        aiogram_update = types.Update(**update)
        dispatcher = webhook_dp
        await dispatcher.feed_update(bot=bot, update=aiogram_update)

    finally:
        await bot.session.close()
