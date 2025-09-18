# rag_system/utils.py
from django.conf import settings
from sentence_transformers import SentenceTransformer
import os


def get_embedding_model():
    if not hasattr(settings, "EMBEDDINGMODEL"):
        model_path = os.path.join(settings.BASE_DIR, "models/multilingual-e5-base")
        settings.EMBEDDINGMODEL = SentenceTransformer(model_path)
    return settings.EMBEDDINGMODEL
