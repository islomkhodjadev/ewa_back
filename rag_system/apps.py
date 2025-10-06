from django.apps import AppConfig

from django.conf import settings


import os
import sys

SKIP_CMDS = {
    "collectstatic",
    "makemigrations",
    "migrate",
    "showmigrations",
    "check",
    "shell",
    "dbshell",
    "createsuperuser",
    "loaddata",
    "dumpdata",
    "test",
    "compilemessages",
    "makemessages",
}


def _is_management_command():
    return len(sys.argv) > 1 and sys.argv[1] in SKIP_CMDS


def _is_primary_process():
    """
    Avoid double-exec in DEBUG autoreload. When DEBUG=True, Django spawns a
    reloader; only run in the "main" child process.
    """
    if settings.DEBUG:
        return os.environ.get("RUN_MAIN") == "true"
    return True


def _is_celery_worker():
    """Check if this is a Celery worker using env variable"""
    return os.environ.get("CELERY_WORKER") == "true"


class RagSystemConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "rag_system"

    def ready(self):
        import rag_system.signals

        if _is_management_command():
            return
        if not _is_primary_process():
            return

        # ONLY load model if CELERY_WORKER env var is set
        if not _is_celery_worker():
            return

        # Load model only in workers
        try:
            from rag_system.utils import get_embedding_model

            get_embedding_model()
        except Exception as exc:
            import logging

            logging.getLogger(__name__).exception("Embedding warmup failed: %s", exc)
