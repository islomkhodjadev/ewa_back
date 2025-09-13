# embeddings.py

# model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

import re
from django.conf import settings
from .model import get_embedding_model

import asyncio


async def get_embedding_async(text: str):
    clean = normalize_text(text)
    return await asyncio.to_thread(lambda: get_embedding_model().encode(clean).tolist())


def normalize_text(text: str) -> str:
    print(text)
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_embedding(text: str):
    clean = normalize_text(text)
    return get_embedding_model().encode(clean).tolist()
