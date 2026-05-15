"""
Celery app factory.

Broker: Redis
Result backend: Redis
Task serializer: JSON

Start worker:
    celery -A src.workers.celery_app worker -Q default --loglevel=info

Start beat scheduler (for periodic tasks):
    celery -A src.workers.celery_app beat --loglevel=info
"""
from celery import Celery
from celery.schedules import crontab

from src.config import get_settings


def create_celery() -> Celery:
    """Create and configure Celery application."""
    settings = get_settings()
    app = Celery(
        "ai_meeting_assistant",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
    )
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        result_expires=3600,
    )

    app.conf.include = [
        "src.workers.pipeline",
        "src.workers.tasks.transcribe_task",
        "src.workers.tasks.stream_finalize_task",
        "src.workers.tasks.analyze_task",
        "src.workers.tasks.jira_push_task",
        "src.workers.tasks.cleanup_task",
    ]

    app.conf.beat_schedule = {
        "cleanup-old-recordings": {
            "task": "cleanup_recordings",
            "schedule": crontab(minute=0, hour="*/2"),
            "options": {"queue": "default"},
        },
    }

    return app


celery_app = create_celery()
