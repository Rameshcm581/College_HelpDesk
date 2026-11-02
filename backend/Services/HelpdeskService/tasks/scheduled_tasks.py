# backend/Services/HelpdeskService/tasks/scheduled_tasks.py
"""Celery Beat Scheduled Tasks.

Tasks registered here are executed periodically by the Celery Beat scheduler.
The beat schedule is configured in celery_app.py.

Registered tasks
----------------
- scheduled_rescan_web_documents  : Re-indexes any document whose source is a
  website URL so the knowledge base stays up-to-date with the live college portal.
- scheduled_database_backup       : Invokes pg_dump via subprocess and stores the
  snapshot in the configured backup directory (mirrors the logic in scripts/backup.sh).
"""

import asyncio
import datetime
import logging
import os
import pathlib
import subprocess
from typing import Any, Dict

from sqlalchemy import select

from celery_app import celery_app
from configs.base_config import BaseConfig
from models import async_session_factory
from models.models import Documents, DocumentVersions, IngestionJobs, JobStatus

logger = logging.getLogger(__name__)


# ── Web Document Re-scan ─────────────────────────────────────────────────────

async def _trigger_web_document_rescan() -> Dict[str, Any]:
    """Queries all ACTIVE documents whose source is a WEBSITE_URL, then
    creates a new QUEUED ingestion job for each so the Celery worker re-fetches,
    parses, and re-indexes their latest content.
    Returns a summary dict with the count of jobs queued.
    """
    from tasks.ingestion_tasks import task_extract_document  # noqa: PLC0415 – local import avoids circular

    queued = 0
    errors = 0

    async with async_session_factory() as db:
        # Find all completed WEBSITE_URL ingestion jobs linked to active documents
        result = await db.execute(
            select(IngestionJobs)
            .join(DocumentVersions, IngestionJobs.version_id == DocumentVersions.id)
            .join(Documents, DocumentVersions.document_id == Documents.id)
            .where(
                IngestionJobs.job_type == "WEBSITE_URL",
                IngestionJobs.status == JobStatus.COMPLETED,
                Documents.status.in_(["ACTIVE", "PUBLISHED"]),
            )
            # Keep only the most recent job per version to avoid redundant re-runs
            .order_by(IngestionJobs.completed_at.desc())
        )
        jobs = result.scalars().all()

        # De-duplicate by version_id (keep the latest completed job per version)
        seen_versions: set = set()
        for job in jobs:
            if job.version_id in seen_versions:
                continue
            seen_versions.add(job.version_id)

            # Create a new extraction job for this version
            new_job = IngestionJobs(
                version_id=job.version_id,
                job_type="WEBSITE_URL",
                status=JobStatus.QUEUED,
                source_url=job.source_url,
                job_metadata=job.job_metadata,
                max_retries=3,
            )
            db.add(new_job)
            await db.flush()

            try:
                task_extract_document.delay(str(new_job.id))
                queued += 1
                logger.info("Scheduled rescan queued job %s for URL %s", new_job.id, job.source_url)
            except Exception as exc:
                logger.warning("Could not dispatch rescan job %s: %s", new_job.id, exc)
                errors += 1

        await db.commit()

    result_summary = {
        "run_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "web_docs_requeued": queued,
        "dispatch_errors": errors,
    }
    logger.info("Scheduled web rescan complete: %s", result_summary)
    return result_summary


@celery_app.task(name="app.tasks.scheduled.rescan_web_documents", bind=True, max_retries=1)
def scheduled_rescan_web_documents(self):
    """Celery Beat task: re-indexes all active WEBSITE_URL documents.
    Runs daily at 02:00 IST (configurable via SCRAPER_SCHEDULE_CRON env var).
    """
    logger.info("Celery Beat: starting scheduled web document rescan.")
    try:
        return asyncio.run(_trigger_web_document_rescan())
    except Exception as exc:
        logger.error("Scheduled web rescan failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=300)  # Retry once after 5 min


# ── Database Backup ──────────────────────────────────────────────────────────

def _run_pg_dump(backup_dir: pathlib.Path) -> Dict[str, Any]:
    """Runs pg_dump using SYNC_DB_URI and writes a timestamped .dump file.
    Returns a dict with the snapshot path and size on success.
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_path = backup_dir / f"helpdesk_db_{timestamp}.dump"

    sync_uri = BaseConfig.SYNC_DB_URI

    try:
        result = subprocess.run(
            [
                "pg_dump",
                "--format=custom",
                "--no-password",
                "--dbname", sync_uri,
                "--file", str(dump_path),
            ],
            capture_output=True,
            text=True,
            timeout=300,
            check=True,
        )
        size_kb = dump_path.stat().st_size // 1024
        logger.info("Database backup created: %s (%d KB)", dump_path, size_kb)
        return {
            "path": str(dump_path),
            "size_kb": size_kb,
            "timestamp": timestamp,
            "status": "success",
        }
    except subprocess.CalledProcessError as exc:
        logger.error("pg_dump failed (exit %s): %s", exc.returncode, exc.stderr)
        if dump_path.exists():
            dump_path.unlink(missing_ok=True)
        return {"status": "failed", "error": exc.stderr or str(exc)}
    except FileNotFoundError:
        logger.error("pg_dump binary not found on PATH. Backup skipped.")
        return {"status": "skipped", "reason": "pg_dump not found"}
    except Exception as exc:
        logger.error("Unexpected backup error: %s", exc, exc_info=True)
        return {"status": "failed", "error": str(exc)}


@celery_app.task(name="app.tasks.scheduled.database_backup", bind=True, max_retries=1)
def scheduled_database_backup(self):
    """Celery Beat task: creates a pg_dump snapshot of the production database.
    Runs nightly at 03:00 IST (configurable via DB_BACKUP_SCHEDULE_CRON env var).
    """
    backup_dir_env = os.getenv("BACKUP_DIR", "")
    if backup_dir_env:
        backup_dir = pathlib.Path(backup_dir_env)
    else:
        # Default: <project_root>/backups/
        backup_dir = pathlib.Path(__file__).parent.parent.parent.parent.parent.parent / "backups"

    logger.info("Celery Beat: starting scheduled database backup to %s", backup_dir)
    try:
        result = _run_pg_dump(backup_dir)
        return result
    except Exception as exc:
        logger.error("Scheduled database backup task failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=600)  # Retry once after 10 min
