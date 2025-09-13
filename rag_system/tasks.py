from celery import shared_task
from rag_system.utils import get_answer_sync
import json
from asgiref.sync import sync_to_async, async_to_sync
from rag_system.models import Embedding
from rag_system.serializers import EmbeddingSerializer

from channels.layers import get_channel_layer
from miniapp.models import Message


@shared_task(bind=True)
def answer_question(self, prompt, group, session_id):
    try:
        result = get_answer_sync(prompt)
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
        ai_msg = Message.objects.create(
            session_id=session_id,
            owner="ai",  # or Message.AI if you defined the constant
            message=answer_text,
            embedding_id=embedding_id,  # None is fine if no embedding
        )
        response = {
            "id": embedding_id,
            "answer": payload.get("answer"),
            "embedding": embedding_data,
        }
        async_to_sync(channel_layer.group_send)(
            group, {"type": "notify", "data": response}
        )
    except Exception as e:
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


def _fetch_embedding_serialized(embedding_id: int):
    obj = Embedding.objects.prefetch_related("data").filter(id=embedding_id).first()
    if not obj:
        return None
    # If you need absolute file URLs, pass {"request": request} from a DRF view.
    return EmbeddingSerializer(obj, context={}).data
