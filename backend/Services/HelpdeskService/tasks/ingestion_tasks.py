# backend/Services/HelpdeskService/tasks/ingestion_tasks.py
import asyncio
import datetime
import logging
import pathlib
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from celery_app import celery_app
from models import async_session_factory
from models.models import (
    AcademicYears,
    Departments,
    DocumentChunks,
    DocumentStatus,
    DocumentVersions,
    Documents,
    IngestionJobs,
    JobStatus,
)
from resources.aiService import get_embedding_provider
from resources.pdfService import pdf_service
from resources.webScraperService import web_scraper_service

logger = logging.getLogger(__name__)


async def execute_document_extraction_job(job_id: uuid.UUID) -> Dict[str, Any]:
    """Extracts text from PDF or Web URL, generates preview, detects scanned pages,
    and updates version status to REVIEW_REQUIRED.
    Supports retries and records error messages on failure.
    """
    async with async_session_factory() as db:
        job = await db.get(IngestionJobs, job_id)
        if not job:
            raise ValueError(f"IngestionJob with id {job_id} not found.")

        version = await db.get(DocumentVersions, job.version_id)
        if not version:
            raise ValueError(f"DocumentVersion with id {job.version_id} not found.")

        doc = await db.get(Documents, version.document_id)

        job.status = JobStatus.PROCESSING
        job.updated_at = datetime.datetime.now(datetime.timezone.utc)
        version.status = DocumentStatus.PROCESSING
        if doc and doc.status == DocumentStatus.UPLOADED:
            doc.status = DocumentStatus.PROCESSING

        await db.commit()

        try:
            pages = []
            extracted_title = None

            if job.job_type == "PDF_UPLOAD":
                file_path = pathlib.Path(version.storage_path)
                if not file_path.exists():
                    raise FileNotFoundError(f"Stored PDF file missing at {file_path}")
                content = file_path.read_bytes()
                # Run PDF extraction (allowing OCR on scanned pages)
                pages = pdf_service.extract_pages(content, allow_ocr=True)

            elif job.job_type == "WEBSITE_URL":
                source_url = job.source_url or (job.job_metadata or {}).get("source_url")
                if not source_url:
                    raise ValueError("Source URL is missing for WEBSITE_URL ingestion job.")
                final_url, content_type, html_bytes = await web_scraper_service.fetch_url_content(source_url)
                extracted_title, pages = web_scraper_service.parse_web_content(html_bytes, final_url)
                if extracted_title and doc and doc.title == "Web Ingestion":
                    doc.title = extracted_title

            else:
                raise ValueError(f"Unsupported job_type: {job.job_type}")

            # Assemble preview text for staff review
            preview_snippets = []
            for p in pages:
                tag = f"[Page {p.page_number}]" + (" (OCR Scanned)" if p.is_scanned else "")
                snippet = p.text[:500] if len(p.text) > 500 else p.text
                preview_snippets.append(f"{tag}\n{snippet}")

            full_preview = "\n\n---\n\n".join(preview_snippets)

            # Update DocumentVersion
            version.extracted_text_preview = full_preview[:8000]
            version.page_count = len(pages)
            version.status = DocumentStatus.REVIEW_REQUIRED
            version.updated_at = datetime.datetime.now(datetime.timezone.utc)

            if doc and doc.status == DocumentStatus.PROCESSING:
                doc.status = DocumentStatus.REVIEW_REQUIRED

            # Mark job complete
            job.status = JobStatus.COMPLETED
            job.error_message = None
            job.completed_at = datetime.datetime.now(datetime.timezone.utc)
            job.updated_at = datetime.datetime.now(datetime.timezone.utc)

            await db.commit()
            return {"job_id": str(job.id), "status": "COMPLETED", "page_count": len(pages)}

        except Exception as exc:
            logger.error("Job %s extraction failure: %s", job_id, exc, exc_info=True)
            job.retry_count += 1
            job.error_message = str(exc)
            job.updated_at = datetime.datetime.now(datetime.timezone.utc)

            if job.retry_count < job.max_retries:
                # Re-queue for safe retry
                job.status = JobStatus.QUEUED
                version.status = DocumentStatus.UPLOADED
            else:
                job.status = JobStatus.FAILED
                version.status = DocumentStatus.FAILED
                if doc and doc.active_version_id is None:
                    doc.status = DocumentStatus.FAILED

            await db.commit()
            return {"job_id": str(job.id), "status": job.status.value, "error": str(exc)}


async def execute_document_indexing_job(job_id: uuid.UUID) -> Dict[str, Any]:
    """Executed after staff approval. Chunks text, generates pgvector embeddings,
    stores chunks linked to version_id, and safely activates the new version
    (archiving the previous active version without downtime).
    """
    async with async_session_factory() as db:
        job = await db.get(IngestionJobs, job_id)
        if not job:
            raise ValueError(f"IngestionJob with id {job_id} not found.")

        version = await db.get(DocumentVersions, job.version_id)
        if not version:
            raise ValueError(f"DocumentVersion with id {job.version_id} not found.")

        doc = await db.get(Documents, version.document_id)
        if not doc:
            raise ValueError(f"Document with id {version.document_id} not found.")

        ay = await db.get(AcademicYears, doc.academic_year_id)
        dept = await db.get(Departments, doc.department_id)

        job.status = JobStatus.PROCESSING
        job.updated_at = datetime.datetime.now(datetime.timezone.utc)
        version.status = DocumentStatus.INDEXING
        await db.commit()

        try:
            pages = []
            if job.job_type == "PDF_UPLOAD":
                file_path = pathlib.Path(version.storage_path)
                pages = pdf_service.extract_pages(file_path.read_bytes(), allow_ocr=True)
            elif job.job_type in ("WEBSITE_URL", "INDEXING"):
                source_url = job.source_url or (job.job_metadata or {}).get("source_url")
                if source_url:
                    _, _, html_bytes = await web_scraper_service.fetch_url_content(source_url)
                    _, pages = web_scraper_service.parse_web_content(html_bytes, source_url)
                else:
                    # Fallback to re-reading storage_path if available
                    file_path = pathlib.Path(version.storage_path)
                    if file_path.exists():
                        pages = pdf_service.extract_pages(file_path.read_bytes(), allow_ocr=True)

            # Generate chunks
            chunks_data = pdf_service.chunk_document(
                pages=pages,
                document_title=doc.title,
                academic_year=ay.code if ay else "2025-2026",
                department=dept.name if dept else "GENERAL",
                version_id=version.id,
            )

            # Generate embeddings via provider
            embedder = get_embedding_provider()
            chunk_texts = [c.content for c in chunks_data]
            embeddings = await embedder.get_embeddings_batch(chunk_texts) if chunk_texts else []

            # Clean any previously existing chunks for this specific version (idempotency)
            await db.execute(delete(DocumentChunks).where(DocumentChunks.version_id == version.id))

            # Store new chunks
            for c_data, emb in zip(chunks_data, embeddings):
                chunk_rec = DocumentChunks(
                    document_id=doc.id,
                    version_id=version.id,
                    chunk_index=c_data.chunk_index,
                    page_number=c_data.page_number,
                    content=c_data.content,
                    token_count=c_data.token_count,
                    embedding=emb,
                    chunk_metadata=c_data.metadata,
                )
                db.add(chunk_rec)

            version.chunk_count = len(chunks_data)
            version.status = DocumentStatus.ACTIVE
            version.updated_at = datetime.datetime.now(datetime.timezone.utc)

            # SAFE REPLACEMENT LOGIC:
            # Only archive old active version once new version successfully indexes!
            if doc.active_version_id and doc.active_version_id != version.id:
                old_version = await db.get(DocumentVersions, doc.active_version_id)
                if old_version:
                    old_version.status = DocumentStatus.ARCHIVED
                    old_version.updated_at = datetime.datetime.now(datetime.timezone.utc)

            # Update document to point to this newly verified active version
            doc.active_version_id = version.id
            doc.version_number = version.version_number
            doc.status = DocumentStatus.ACTIVE
            doc.updated_at = datetime.datetime.now(datetime.timezone.utc)

            # Mark job complete
            job.status = JobStatus.COMPLETED
            job.error_message = None
            job.completed_at = datetime.datetime.now(datetime.timezone.utc)
            job.updated_at = datetime.datetime.now(datetime.timezone.utc)

            await db.commit()
            return {"job_id": str(job.id), "status": "COMPLETED", "chunks_stored": len(chunks_data)}

        except Exception as exc:
            logger.error("Job %s indexing failure: %s", job_id, exc, exc_info=True)
            job.retry_count += 1
            job.error_message = str(exc)
            job.updated_at = datetime.datetime.now(datetime.timezone.utc)

            # On failure: old active version remains active and untouched!
            job.status = JobStatus.FAILED
            version.status = DocumentStatus.FAILED
            await db.commit()
            return {"job_id": str(job.id), "status": "FAILED", "error": str(exc)}


# Celery Tasks
@celery_app.task(name="app.tasks.ingestion.extract_document", bind=True, max_retries=3)
def task_extract_document(self, job_id_str: str):
    """Celery background worker task for text extraction."""
    job_uuid = uuid.UUID(job_id_str)
    try:
        return asyncio.run(execute_document_extraction_job(job_uuid))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5)


@celery_app.task(name="app.tasks.ingestion.index_document", bind=True, max_retries=3)
def task_index_document(self, job_id_str: str):
    """Celery background worker task for chunk embedding and activation."""
    job_uuid = uuid.UUID(job_id_str)
    try:
        return asyncio.run(execute_document_indexing_job(job_uuid))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5)


def queue_ingestion_job(job_id: uuid.UUID, task_type: str = "extract") -> None:
    """Dispatches job to Celery worker if Redis is reachable,
    or falls back to background async execution.
    """
    try:
        if task_type == "extract":
            task_extract_document.delay(str(job_id))
        else:
            task_index_document.delay(str(job_id))
    except Exception as exc:
        logger.warning("Celery dispatch unavailable (%s). Falling back to direct task executor.", exc)
        if task_type == "extract":
            asyncio.create_task(execute_document_extraction_job(job_id))
        else:
            asyncio.create_task(execute_document_indexing_job(job_id))
