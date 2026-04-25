"""
Celery task: cleanup old audio files based on retention policy.

This task can be scheduled to run periodically (e.g., hourly) to clean up
old recordings that exceed the retention period.

Usage:
    # Manual trigger
    from src.workers.tasks.cleanup_task import cleanup_recordings
    cleanup_recordings.delay()

    # Periodic schedule (add to celery beat config)
    app.conf.beat_schedule = {
        'cleanup-recordings': {
            'task': 'cleanup_recordings',
            'schedule': crontab(minute=0, hour='*'),  # Every hour
        },
    }
"""
from src.config import get_logger
from src.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    name="cleanup_recordings",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
    queue="default",
)
def cleanup_recordings(self) -> dict:
    """
    Clean up old audio recordings based on retention policy.

    Returns:
        Dict with deleted_count and any errors.
    """
    from src.services.cleanup_service import cleanup_old_recordings, get_recordings_summary

    try:
        before_summary = get_recordings_summary()
        logger.info(
            "[cleanup_task] Starting cleanup. Current files: %d, size: %.2f MB",
            before_summary["count"],
            before_summary["total_size_mb"],
        )

        deleted_count = cleanup_old_recordings()

        after_summary = get_recordings_summary()
        logger.info(
            "[cleanup_task] Cleanup complete. Deleted: %d files. "
            "Remaining: %d files, %.2f MB",
            deleted_count,
            after_summary["count"],
            after_summary["total_size_mb"],
        )

        return {
            "deleted_count": deleted_count,
            "remaining_count": after_summary["count"],
            "remaining_size_mb": after_summary["total_size_mb"],
        }

    except Exception as exc:
        logger.error("[cleanup_task] Error during cleanup: %s", exc)
        raise self.retry(exc=exc)
