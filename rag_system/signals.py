# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from rag_system.models import Embedding

# from rag_system.tasks import save_embedding_with_vector_task  # Import the task


# @receiver(post_save, sender=Embedding)
# def create_embedding(sender, instance, created, **kwargs):
#     # Skip if this is the second save from the task itself to avoid loops
#     if hasattr(instance, "_embedding_processing"):
#         return

#     if created and not instance.embedded_vector and instance.raw_text:
#         # Use Celery task instead of direct embedding call
#         save_embedding_with_vector_task.delay(instance.id, instance.raw_text)
