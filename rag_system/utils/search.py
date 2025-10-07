from rag_system.models import Embedding
from .embeddings import get_embedding
from pgvector.django import CosineDistance


def search_documents(query, top_k=5):
    return list(
        Embedding.objects.order_by(CosineDistance("embedded_vector", query))[:top_k]
    )


import asyncio
from .embeddings import get_embedding_async  # your async/sync function


async def search_documents_async(query, top_k=5):

    def run_query():
        return list(
            Embedding.objects.order_by(CosineDistance("embedded_vector", query))[:top_k]
        )

    return await asyncio.to_thread(run_query)
