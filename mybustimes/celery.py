# mybustimes/celery.py

import os
from celery import Celery
from celery.signals import worker_process_init, task_prerun, task_postrun, beat_init

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mybustimes.settings")

app = Celery("mybustimes")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()


@worker_process_init.connect
def _celery_worker_process_init(**kwargs):
    """Ensure stale DB connections are closed when a prefork child is forked."""
    try:
        from django.db import close_old_connections

        close_old_connections()
    except Exception:
        pass


@task_prerun.connect
def _celery_task_prerun(**kwargs):
    try:
        from django.db import close_old_connections

        close_old_connections()
    except Exception:
        pass


@task_postrun.connect
def _celery_task_postrun(**kwargs):
    try:
        from django.db import close_old_connections

        close_old_connections()
    except Exception:
        pass


@beat_init.connect
def _celery_beat_init(**kwargs):
    try:
        from django.db import close_old_connections

        close_old_connections()
    except Exception:
        pass
