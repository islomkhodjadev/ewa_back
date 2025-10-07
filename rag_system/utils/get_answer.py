from . import chat_gpt_function_calling
from rag_system.utils.embeddings import get_embedding_async, get_embedding
from rag_system.utils.search import search_documents_async, search_documents
from typing import Optional, Dict
from miniapp.models import ChatSession


async def get_answer_async(prompt: str) -> Optional[Dict]:
    embedding = await get_embedding_async(prompt)
    objects = await search_documents_async(embedding, top_k=5)

    result = await chat_gpt_function_calling.get_answer_gpt_function_async(
        prompt, objects
    )

    return result


import logging

logger = logging.getLogger(__name__)


def get_answer_sync(prompt: str, session: ChatSession) -> Optional[Dict]:
    embedding = get_embedding(prompt)
    objects = search_documents(embedding, top_k=5)
    logger.info(objects)
    result = chat_gpt_function_calling.get_answer_gpt_function(prompt, objects, session)

    return result
