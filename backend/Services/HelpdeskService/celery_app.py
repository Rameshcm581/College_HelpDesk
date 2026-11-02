# backend/Services/HelpdeskService/celery_app.py
from celery import Celery
from celery.schedules import crontab
from configs.base_config import BaseConfig


def _parse_cron(cron_str: str) -> crontab:
    """Converts a 5-field cron string (min hour dom month dow) into a celery crontab."""
    parts = cron_str.split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {cron_str!r}. Expected 5 fields.")
    minute, hour, day_of_month, month_of_year, day_of_week = parts
    return crontab(
        minute=minute,
        hour=hour,
        day_of_month=day_of_month,
        month_of_year=month_of_year,
        day_of_week=day_of_week,
    )


celery_app = Celery(
    "helpdesk_worker",
    broker=BaseConfig.REDIS_URL,
    backend=BaseConfig.REDIS_URL,
)

# ── Beat schedule (built dynamically so cron strings come from env vars) ───────
_beat_schedule = {}
if BaseConfig.CELERY_BEAT_ENABLED:
    _beat_schedule = {
        "daily-web-document-rescan": {
            "task": "app.tasks.scheduled.rescan_web_documents",
            # Default: 02:00 IST daily. Override via SCRAPER_SCHEDULE_CRON env var.
            "schedule": _parse_cron(BaseConfig.SCRAPER_SCHEDULE_CRON),
            "options": {"queue": "queue_scheduled"},
        },
        "nightly-database-backup": {
            "task": "app.tasks.scheduled.database_backup",
            # Default: 03:00 IST daily. Override via DB_BACKUP_SCHEDULE_CRON env var.
            "schedule": _parse_cron(BaseConfig.DB_BACKUP_SCHEDULE_CRON),
            "options": {"queue": "queue_scheduled"},
        },
    }

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_routes={
        "app.tasks.ingestion.*": {"queue": "queue_ingestion"},
        "app.tasks.notifications.*": {"queue": "queue_notifications"},
        "app.tasks.scheduled.*": {"queue": "queue_scheduled"},
    },
    beat_schedule=_beat_schedule,
)


@celery_app.task(name="tasks.ping")
def celery_ping():
    """Worker health check task."""
    return "PONG"


# Ensure task registration
try:
    import tasks.ingestion_tasks  # noqa: F401
    import tasks.scheduled_tasks  # noqa: F401
except ImportError:
    pass
