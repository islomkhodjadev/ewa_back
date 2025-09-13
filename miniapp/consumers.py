# consumers.py
import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from miniapp.models import ChatSession, Message
from telegram_client.models import BotClient
from miniapp.serializers import ChatSessionSerializer
from rag_system.tasks import answer_question


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
        return ChatSessionSerializer(session).data if session else None

    # ------------------------------- WS lifecycle ----------------------------------

    async def connect(self):
        chat_id = self.scope["url_route"]["kwargs"].get("user_id")
        print(chat_id, "comming hereeee############")
        if not chat_id:
            await self.close(code=4000)
            return

        ids = await self._ensure_session_get_ids(chat_id=chat_id)
        if not ids:
            await self.close(code=4001)  # no BotClient for this user
            return

        self.bot_client_id, self.chat_session_id = ids

        self.group = f"user_{chat_id}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

        data = await self._get_session_serialized(self.chat_session_id)
        if data:
            await self.send_json(data)

    async def receive_json(self, content, **kwargs):
        prompt = content.get("prompt") or ""
        await self._create_message(self.chat_session_id, prompt, owner="user")

        # kick off your background task (uses stored IDs/group)
        group = self.group
        res = answer_question.delay(
            prompt=prompt, group=group, session_id=self.chat_session_id
        )
        await self.send_json({"status": "accepted", "task_id": res.id})

    async def notify(self, event):
        await self.send_json(event["data"])

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)
