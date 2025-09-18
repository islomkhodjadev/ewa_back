# rag_system/utils.py
from django.conf import settings
from sentence_transformers import SentenceTransformer
import os
from pathlib import Path


def get_embedding_model():
    if not hasattr(settings, "EMBEDDINGMODEL"):
        # Use parent directory for shared model storage
        models_dir = (
            Path(__file__).parent.parent.parent / "models"
        )  # ../models from project root
        model_path = models_dir / "multilingual-e5-base"

        # Ensure models directory exists
        models_dir.mkdir(exist_ok=True)

        # Quick validation check
        if not is_model_valid(str(model_path)):
            print(f"Model not found or invalid at {model_path}, downloading...")
            # This triggers download to the shared location
            model_path.mkdir(exist_ok=True)

        settings.EMBEDDINGMODEL = SentenceTransformer(str(model_path))
    return settings.EMBEDDINGMODEL


def is_model_valid(model_path):
    """Quick check if model is complete"""
    model_dir = Path(model_path)
    if not model_dir.exists():
        return False

    # Check for essential files
    essential_files = ["config.json", "tokenizer.json"]
    for file_name in essential_files:
        if not (model_dir / file_name).exists():
            return False

    # Check for model weights
    weight_files = list(model_dir.glob("*.bin")) + list(model_dir.glob("*.safetensors"))
    if not weight_files:
        return False

    # Basic size check (should be > 100MB total)
    total_size = sum(f.stat().st_size for f in model_dir.rglob("*") if f.is_file())
    if total_size < 100 * 1024 * 1024:  # Less than 100MB
        return False

    return True
