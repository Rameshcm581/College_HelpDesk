# backend/Services/HelpdeskService/celery_app.py
from celery import Celery
from configs.base_config import BaseConfig

celery_app = Celery(
    "helpdesk_worker",
    broker=BaseConfig.REDIS_URL,
    backend=BaseConfig.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_routes={
        "app.tasks.ingestion.*": {"queue": "queue_ingestion"},
        "app.tasks.notifications.*": {"queue": "queue_notifications"},
    },
)


@celery_app.task(name="tasks.ping")
def celery_ping():
    """Worker health check task."""
    return "PONG"

# Ensure task registration
try:
    import tasks.ingestion_tasks  # noqa: F401
except ImportError:
    pass
