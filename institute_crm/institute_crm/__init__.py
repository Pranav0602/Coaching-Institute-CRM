# Load the Celery app when Django starts so that @shared_task decorators
# bind to the configured app without extra imports in every module.
from .celery import app as celery_app

__all__ = ("celery_app",)
