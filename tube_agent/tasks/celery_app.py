"""Celery application configuration."""

from celery import Celery

from tube_agent.config import get_settings

settings = get_settings()

celery_app = Celery(
    "tube_agent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "tube_agent.tasks.fetch.*": {"queue": "default"},
        "tube_agent.tasks.analyze.*": {"queue": "analysis"},
    },
    task_default_queue="default",
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

celery_app.autodiscover_tasks(["tube_agent.tasks"])
