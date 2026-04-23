"""
Celery app factory.

Broker: Redis
Result backend: Redis
Task serializer: JSON

Khởi chạy worker:
    celery -A src.workers.celery_app worker -Q default --loglevel=info
"""
from celery import Celery

from src.config import get_settings


def create_celery() -> Celery:
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
        result_expires=3600,  # Job results hết hạn sau 1 giờ
    )
    # Explicit include cho tất cả task modules
    app.conf.include = [
        "src.workers.pipeline",
        "src.workers.tasks.transcribe_task",
        "src.workers.tasks.analyze_task",
        "src.workers.tasks.jira_push_task",
    ]
    return app


celery_app = create_celery()
