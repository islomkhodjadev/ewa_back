# rag_system/utils.py
from django.conf import settings
from sentence_transformers import SentenceTransformer
import os
from pathlib import Path
import shutil
from safetensors import SafetensorError  # Import this for specific catching


def get_embedding_model():
    if not hasattr(settings, "EMBEDDINGMODEL"):
        # Use parent directory for shared model storage
        models_dir = (
            Path(__file__).parent.parent.parent / "models"
        )  # ../models from project root
        model_path = models_dir / "multilingual-e5-base"

        # Ensure models directory exists
        models_dir.mkdir(exist_ok=True)

        try:
            # Try to load the model first
            settings.EMBEDDINGMODEL = SentenceTransformer(str(model_path))
        except (SafetensorError, Exception) as e:
            # If any error (corruption or missing), remove and redownload
            print(f"Error loading model: {e}")
            print(
                f"Removing potentially corrupted model at {model_path} and redownloading..."
            )

            if model_path.exists():
                shutil.rmtree(model_path)

            # Redownload fresh model
            print("Downloading fresh model...")
            temp_model = SentenceTransformer("intfloat/multilingual-e5-base")
            model_path.mkdir(parents=True, exist_ok=True)
            temp_model.save(str(model_path))

            # Load the fresh model
            settings.EMBEDDINGMODEL = SentenceTransformer(str(model_path))

        print(f"Model loaded successfully from {model_path}")

    return settings.EMBEDDINGMODEL
