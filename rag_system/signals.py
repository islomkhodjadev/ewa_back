# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from rag_system.models import Embedding
from rag_system.utils.embeddings import get_embedding


@receiver(post_save, sender=Embedding)
def create_embedding(sender, instance, created, **kwargs):

    if created and not instance.embedded_vector:
        instance.embedded_vector = get_embedding(instance.raw_text)
        instance.save(update_fields=["embedded_vector"])
