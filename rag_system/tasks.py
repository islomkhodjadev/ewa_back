import json

from celery import shared_task
from rag_system.utils import (
    get_answer_sync,
    skynet_summarize,
    get_answer__skynet_sync,
    skynet_introduce,
)

from rag_system.models import ChatTypes, Roles
from asgiref.sync import sync_to_async, async_to_sync
from rag_system.models import Embedding
from rag_system.serializers import EmbeddingSerializer

from channels.layers import get_channel_layer
from miniapp.models import Message, ChatSession
import logging

logger = logging.getLogger(__name__)


def _fetch_embedding_serialized(embedding_id: int):

    if str(embedding_id) == "-1" or (type(embedding_id) == int and embedding_id == -1):
        return None

    obj = Embedding.objects.prefetch_related("data").filter(id=embedding_id).first()
    if not obj:
        return None
    # If you need absolute file URLs, pass {"request": request} from a DRF view.
    return EmbeddingSerializer(obj, context={}).data


@shared_task(bind=True)
def answer_question(self, prompt, group, session_id):
    try:
        session = ChatSession.objects.get(pk=session_id)

        if session.mode == ChatSession.CHAT:
            response = chat(prompt, group, session, self.request.id)
        elif session.mode == ChatSession.SKYNET:
            response = skynet_chat(prompt, group, session, self.request.id)

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            group, {"type": "notify", "data": response}
        )

    except Exception as e:

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            group,
            {
                "type": "notify",
                "data": {
                    "status": "failure",
                    "task_id": self.request.id,
                    "error": str(e),
                },
            },
        )
        raise


def chat(prompt, group, session, taskId):
    try:

        result = get_answer_sync(prompt, session)

        channel_layer = get_channel_layer()
        # normalize result -> dict
        if isinstance(result, str):
            try:
                payload = json.loads(result)
            except json.JSONDecodeError:
                payload = {"answer": result}
        else:
            payload = result or {}

        answer_text = payload.get("answer") or ""

        embedding_id = payload.get("id")
        embedding_data = (
            _fetch_embedding_serialized(embedding_id)
            if embedding_id is not None
            else None
        )
        if embedding_id == -1:
            embedding_id = None

        ai_msg = Message.objects.create(
            session=session,
            owner="system",
            message=answer_text,
            embedding_id=embedding_id,
        )
        response = {
            "id": embedding_id,
            "answer": payload.get("answer"),
            "embedding": embedding_data,
            "task_id": taskId,
        }
        return response
    except Exception as e:
        return {
            "status": "failure",
            "task_id": taskId,
            "error": str(e),
        }


def skynet_chat(prompt, group, session, taskId):
    try:
        answer_text = get_answer__skynet_sync(prompt, session)

        channel_layer = get_channel_layer()

        ai_msg = Message.objects.create(
            session=session,
            owner="system",
            message=answer_text,
        )
        response = {
            "id": None,
            "answer": answer_text,
            "embedding": None,
            "task_id": taskId,
        }
        return response
    except Exception as e:

        return {
            "status": "failure",
            "task_id": taskId,
            "error": str(e),
        }


@shared_task(bind=True)
def change_mode_to_skynet(self, prompt, group, session_id):
    try:
        session = ChatSession.objects.get(pk=session_id)

        session.mode = ChatSession.SKYNET
        session.save()
        logger.info(session)
        channel_layer = get_channel_layer()

        ai_msg = Message.objects.create(
            session=session,
            owner="system",
            summarize_start=True,
            message="""Давай прокачаем твои навыки продаж и приглашений – без стресса, пота и отказов!
Выбирай героя, веди диалог – а в конце получи обратную связь (не больно, обещаю)""",
        )

        roles = [
            {"role_name": role.name, "role_id": role.id} for role in Roles.objects.all()
        ]
        response = {
            "id": None,
            "answer": """Давай прокачаем твои навыки продаж и приглашений – без стресса, пота и отказов!
Выбирай героя, веди диалог – а в конце получи обратную связь (не больно, обещаю)""",
            "embedding": None,
            "task_id": self.request.id,
            "roles": roles,
        }
        logger.info(response)
        async_to_sync(channel_layer.group_send)(
            group, {"type": "notify", "data": response}
        )

    except Exception as e:

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            group,
            {
                "type": "notify",
                "data": {
                    "status": "failure",
                    "task_id": self.request.id,
                    "error": str(e),
                },
            },
        )
        raise


@shared_task(bind=True)
def change_mode_to_chat(self, prompt, group, session_id):
    try:
        session = ChatSession.objects.get(pk=session_id)

        answer = skynet_summarize(session)
        logger.info("chat started working")
        channel_layer = get_channel_layer()

        ai_msg = Message.objects.create(
            session=session, owner="system", message=answer, summarize_end=True
        )

        session.mode = ChatSession.CHAT
        session.current_role = None
        session.save()
        response = {
            "id": None,
            "answer": answer,
            "embedding": None,
            "task_id": self.request.id,
            "buttons": ["/Тренажер"],
        }
        async_to_sync(channel_layer.group_send)(
            group,
            {
                "type": "notify",
                "data": response,
            },
        )

    except Exception as e:

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            group,
            {
                "type": "notify",
                "data": {
                    "status": "failure",
                    "task_id": self.request.id,
                    "error": str(e),
                },
            },
        )
        raise


@shared_task(bind=True)
def entry_role(self, prompt, group, session_id, role_id):
    try:
        session = ChatSession.objects.get(pk=session_id)
        role = Roles.objects.get(id=role_id)
        session.current_role = role
        session.save()

        answer = skynet_introduce(session)

        channel_layer = get_channel_layer()

        ai_msg = Message.objects.create(session=session, owner="system", message=answer)

        response = {
            "id": None,
            "answer": answer,
            "embedding": None,
            "task_id": self.request.id,
            "buttons": ["/ОЦЕНИТЬ"],
        }

        async_to_sync(channel_layer.group_send)(
            group,
            {
                "type": "notify",
                "data": response,
            },
        )

    except Exception as e:

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            group,
            {
                "type": "notify",
                "data": {
                    "status": "failure",
                    "task_id": self.request.id,
                    "error": str(e),
                },
            },
        )
        raise
