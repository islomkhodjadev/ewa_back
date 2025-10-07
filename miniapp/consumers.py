# consumers.py
import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from miniapp.models import ChatSession, Message
from rag_system.utils.get_buttons import get_buttons
from telegram_client.models import BotClient
from miniapp.serializers import ChatSessionSerializer
from rag_system.tasks import (
    answer_question,
    change_mode_to_chat,
    change_mode_to_skynet,
    entry_role,
)
from django.contrib.postgres.aggregates import ArrayAgg

import logging

logger = logging.getLogger(__name__)


class NotificationsConsumer(AsyncJsonWebsocketConsumer):
    # Channels 4.x allows async encode_json
    async def encode_json(self, content):
        return json.dumps(content, ensure_ascii=False)

    # --------------------- DB helpers (SYNC; run in threadpool) ---------------------

    @database_sync_to_async
    def _create_message(self, session_id: int, message: str, owner: str):
        return Message.objects.create(
            session_id=session_id, message=message, owner=owner
        )

    @database_sync_to_async
    def _get_bot_and_session_id(self, chat_id: int):
        """Return (session_id, bot_client_id) or None if no session exists."""
        return (
            ChatSession.objects.filter(bot_client__chat_id=chat_id)
            .values_list("id", "bot_client_id")
            .first()
        )

    @database_sync_to_async
    def _ensure_session_get_ids(self, chat_id: int):
        """
        Ensure BotClient exists for chat_id and ensure a ChatSession for it.
        Return (bot_client_id, chat_session_id) or None if BotClient missing.
        """
        bot = BotClient.objects.filter(chat_id=chat_id).only("id").first()
        if not bot:
            return None
        if not bot.is_verified or not bot.ai_access:
            return None

        session, _created = ChatSession.objects.get_or_create(bot_client=bot)
        return bot.id, session.id

    @database_sync_to_async
    def _get_session_serialized(self, session_id: int):
        """
        Serialize the session with relateds efficiently.
        Adjust prefetch/related_name to your models.
        """
        qs = ChatSession.objects.select_related("bot_client").prefetch_related(
            "messages"
        )  # or "messages" if that's your related_name
        session = qs.filter(pk=session_id).first()
        if session:
            data = ChatSessionSerializer(session).data

            buttons = get_buttons(session)
            if "buttons" in buttons:
                data["buttons"] = buttons["buttons"]
            elif "roles" in buttons:
                data["roles"] = buttons["roles"]
            return data
        return None

    # ------------------------------- WS lifecycle ----------------------------------

    async def connect(self):
        chat_id = self.scope["url_route"]["kwargs"].get("user_id")

        logger.info(f"WebSocket connection attempt for user_id: {chat_id}")

        if not chat_id:
            logger.warning(
                "WebSocket connection rejected: Missing user_id in URL route"
            )
            await self.close(code=4000)
            return

        logger.debug(f"Attempting to get session IDs for chat_id: {chat_id}")
        ids = await self._ensure_session_get_ids(chat_id=chat_id)

        if not ids:
            logger.error(
                f"WebSocket connection rejected: No BotClient found for user_id: {chat_id}"
            )
            await self.close(code=4001)  # no BotClient for this user
            return

        self.bot_client_id, self.chat_session_id = ids
        logger.info(
            f"Session IDs retrieved - bot_client_id: {self.bot_client_id}, chat_session_id: {self.chat_session_id}"
        )

        self.group = f"user_{chat_id}"
        logger.debug(f"Adding channel to group: {self.group}")

        try:
            await self.channel_layer.group_add(self.group, self.channel_name)
            await self.accept()
            logger.info(
                f"WebSocket connection accepted for user_id: {chat_id}, channel: {self.channel_name}"
            )
        except Exception as e:
            logger.error(
                f"Failed to add channel to group or accept connection: {str(e)}"
            )
            await self.close(code=4002)
            return

        logger.debug(
            f"Fetching serialized session data for chat_session_id: {self.chat_session_id}"
        )
        try:
            data = await self._get_session_serialized(self.chat_session_id)

            if data:
                logger.info(f"Sending initial session data to user_id: {chat_id}")
                await self.send_json(data)
                logger.debug("Initial session data sent successfully")
            else:
                logger.warning(
                    f"No session data found for chat_session_id: {self.chat_session_id}"
                )

        except Exception as e:
            logger.error(f"Error fetching or sending session data: {str(e)}")
            await self.close(code=4002)
            return
            # Don't close connection here as the WebSocket is already established
            # Just log the error and continue

    async def receive_json(self, content, **kwargs):
        prompt = content.get("prompt") or ""

        logger.info(prompt)
        await self._create_message(self.chat_session_id, prompt, owner="user")
        group = self.group
        if prompt == "/ОЦЕНИТЬ":
            res = change_mode_to_chat.delay(
                prompt=prompt, group=group, session_id=self.chat_session_id
            )
        # kick off your background task (uses stored IDs/group)
        elif prompt == "/Тренажер":
            res = change_mode_to_skynet.delay(
                prompt=prompt, group=group, session_id=self.chat_session_id
            )
        elif "role_id" in content:
            res = entry_role.delay(
                prompt, group, self.chat_session_id, content.get("role_id")
            )
        else:
            res = answer_question.delay(
                prompt=prompt, group=group, session_id=self.chat_session_id
            )

        await self.send_json({"status": "accepted", "task_id": res.id})

    async def notify(self, event):
        await self.send_json(event["data"])

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)
