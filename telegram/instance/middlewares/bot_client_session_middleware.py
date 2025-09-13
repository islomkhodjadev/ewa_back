from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Awaitable, Any, Dict
from telegram_client.models import BotClient, BotClientSession


class BotClientSessionMiddleWare(BaseMiddleware):

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:

        bot_client, _ = await BotClient.objects.aget_or_create(
            chat_id=int(event.from_user.id)
        )
        bot_client_session, _ = await BotClientSession.objects.aget_or_create(
            client=bot_client
        )
        bot_client_session = await BotClientSession.objects.select_related(
            "client", "current_button"
        ).aget(  # joins in one query
            pk=bot_client_session.pk
        )

        data["session"] = bot_client_session
        data["client"] = bot_client_session.client  # optional shortcut

        return await handler(event, data)
