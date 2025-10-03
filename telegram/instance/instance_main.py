from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.redis import RedisStorage
import redis.asyncio as redis
from aiogram.filters import CommandStart
import os
from telegram.instance import handlers

# Use the same Redis config from your Django settings
REDIS_HOST = os.getenv("REDIS_HOST", "redis")  # docker service name
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Initialize Redis storage for FSM
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=2,  # Use different DB than Celery (0) and Channels (1)
    decode_responses=True,
)
storage = RedisStorage(redis=redis_client)

webhook_dp = Dispatcher(storage=storage)

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
        await webhook_dp.feed_update(bot=bot, update=aiogram_update)
    finally:
        await bot.session.close()
