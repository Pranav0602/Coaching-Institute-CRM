import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "institute_crm.settings")

app = Celery("institute_crm")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
