# backend/Services/HelpdeskService/resources/documentController.py
import datetime
import os
import pathlib
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, Header, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import get_db
from models.models import (
    AcademicYears,
    Departments,
    DocumentStatus,
    DocumentVersions,
    Documents,
    IngestionJobs,
    JobStatus,
    UserRole,
    Users,
)
from resources.authDeps import check_department_scope, get_current_user, require_roles
from resources.errors import ConflictError, FileValidationError, NotFoundError, UnauthorizedError
from resources.pdfService import pdf_service
from resources.schemas import (
    ApiResponse,
    DocumentApprovalRequest,
    DocumentRejectRequest,
    UrlIngestRequest,
)
from resources.utils import calculate_sha256
from resources.webScraperService import web_scraper_service
from tasks.ingestion_tasks import queue_ingestion_job

router = APIRouter()


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _parse_date(date_str: Optional[str]) -> Optional[datetime.date]:
    if not date_str:
        return None
    try:
        return datetime.date.fromisoformat(date_str.strip())
    except ValueError:
        return None


async def _resolve_academic_year(db: AsyncSession, code: str) -> AcademicYears:
    res = await db.execute(select(AcademicYears).where(AcademicYears.code == code))
    ay = res.scalars().first()
    if not ay:
        # Default or fallback to first available
        res_default = await db.execute(select(AcademicYears).order_by(AcademicYears.is_current.desc()))
        ay = res_default.scalars().first()
        if not ay:
            raise NotFoundError(f"Academic year '{code}' not configured in database.")
    return ay


async def _resolve_department(db: AsyncSession, code: str) -> Departments:
    res = await db.execute(select(Departments).where(Departments.code == code))
    dept = res.scalars().first()
    if not dept:
        res_default = await db.execute(select(Departments).order_by(Departments.created_at.asc()))
        dept = res_default.scalars().first()
        if not dept:
            raise NotFoundError(f"Department '{code}' not found in database.")
    return dept


# ── 1. UPLOAD PDF DOCUMENT ───────────────────────────────────────────────────

@router.post("/documents/upload", response_model=ApiResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Admin Documents"])
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    academic_year_code: str = Form("2025-2026"),
    department_code: str = Form("GENERAL"),
    valid_from: Optional[str] = Form(None),
    valid_until: Optional[str] = Form(None),
    change_summary: Optional[str] = Form("Initial document upload"),
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.CONTENT_APPROVER])),
    db: AsyncSession = Depends(get_db),
):
    """Uploads institutional PDF document securely, checks magic headers and size limits,
    deduplicates via SHA-256, stores in safe storage path, and queues asynchronous background extraction.
    """
    file_bytes = await file.read()

    # 1. Validate file format and size
    pdf_service.validate_pdf_content(file_bytes)

    # 2. Checksum and deduplication check
    checksum = calculate_sha256(file_bytes)
    existing_ver = await db.execute(
        select(DocumentVersions)
        .where(DocumentVersions.checksum_sha256 == checksum)
        .where(DocumentVersions.status.in_([DocumentStatus.ACTIVE, DocumentStatus.PUBLISHED, DocumentStatus.REVIEW_REQUIRED]))
    )
    dup = existing_ver.scalars().first()
    if dup:
        raise ConflictError(
            f"An identical document version already exists in state '{dup.status.value}'.",
            details={"existing_document_id": str(dup.document_id), "existing_version_id": str(dup.id)},
        )

    # 3. Resolve metadata foreign keys
    ay = await _resolve_academic_year(db, academic_year_code)
    dept = await _resolve_department(db, department_code)

    # 4. Generate safe storage path and save content
    doc_id = uuid.uuid4()
    storage_path = pdf_service.generate_safe_storage_path(doc_id, version_number=1, original_filename=file.filename or "upload.pdf")
    storage_path.write_bytes(file_bytes)

    # 5. Persist Document & Version records in UPLOADED state
    new_doc = Documents(
        id=doc_id,
        title=title.strip(),
        file_name=file.filename or "document.pdf",
        storage_path=str(storage_path),
        mime_type="application/pdf",
        file_size_bytes=len(file_bytes),
        checksum_sha256=checksum,
        version_number=1,
        status=DocumentStatus.UPLOADED,
        academic_year_id=ay.id,
        department_id=dept.id,
        uploaded_by_id=current_user.id,
    )
    db.add(new_doc)
    await db.flush()

    new_version = DocumentVersions(
        document_id=new_doc.id,
        version_number=1,
        file_name=file.filename or "document.pdf",
        storage_path=str(storage_path),
        mime_type="application/pdf",
        file_size_bytes=len(file_bytes),
        checksum_sha256=checksum,
        status=DocumentStatus.UPLOADED,
        change_summary=change_summary,
        valid_from=_parse_date(valid_from),
        valid_until=_parse_date(valid_until),
        created_by_id=current_user.id,
    )
    db.add(new_version)
    await db.flush()

    # 6. Create IngestionJob record
    job = IngestionJobs(
        document_id=new_doc.id,
        version_id=new_version.id,
        job_type="PDF_UPLOAD",
        status=JobStatus.QUEUED,
        job_metadata={"original_filename": file.filename, "size_bytes": len(file_bytes)},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # 7. Enqueue background extraction task
    queue_ingestion_job(job.id, "extract")

    return ApiResponse(
        success=True,
        data={
            "document_id": str(new_doc.id),
            "version_id": str(new_version.id),
            "job_id": str(job.id),
            "status": DocumentStatus.UPLOADED.value,
            "message": "File uploaded successfully. Processing queued in background worker.",
        },
    )


# ── 2. INGEST WEBSITE URL ────────────────────────────────────────────────────

@router.post("/documents/ingest-url", response_model=ApiResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Admin Documents"])
async def ingest_website_url(
    req: UrlIngestRequest,
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.CONTENT_APPROVER])),
    db: AsyncSession = Depends(get_db),
):
    """Initiates controlled URL ingestion with SSRF defenses, scheme restriction,
    DNS IP validation, and private/internal destination blocking.
    """
    # 1. Defend against SSRF immediately
    web_scraper_service.validate_url_against_ssrf(req.url)

    # 2. Checksum and deduplication
    checksum = calculate_sha256(req.url.encode("utf-8"))
    existing_ver = await db.execute(
        select(DocumentVersions)
        .where(DocumentVersions.checksum_sha256 == checksum)
        .where(DocumentVersions.status.in_([DocumentStatus.ACTIVE, DocumentStatus.PUBLISHED, DocumentStatus.REVIEW_REQUIRED]))
    )
    dup = existing_ver.scalars().first()
    if dup:
        raise ConflictError(
            f"This URL has already been ingested in version '{dup.id}' (state: {dup.status.value}).",
            details={"existing_document_id": str(dup.document_id), "existing_version_id": str(dup.id)},
        )

    ay = await _resolve_academic_year(db, req.academic_year_code)
    dept = await _resolve_department(db, req.department_code)

    doc_id = uuid.uuid4()
    doc_title = req.title.strip() if req.title else "Web Ingestion"

    new_doc = Documents(
        id=doc_id,
        title=doc_title,
        file_name=req.url,
        storage_path=req.url,
        mime_type="text/html",
        file_size_bytes=0,
        checksum_sha256=checksum,
        version_number=1,
        status=DocumentStatus.UPLOADED,
        academic_year_id=ay.id,
        department_id=dept.id,
        uploaded_by_id=current_user.id,
    )
    db.add(new_doc)
    await db.flush()

    new_version = DocumentVersions(
        document_id=new_doc.id,
        version_number=1,
        file_name=req.url,
        storage_path=req.url,
        mime_type="text/html",
        file_size_bytes=0,
        checksum_sha256=checksum,
        status=DocumentStatus.UPLOADED,
        change_summary="Initial website crawl",
        valid_from=_parse_date(req.valid_from),
        valid_until=_parse_date(req.valid_until),
        created_by_id=current_user.id,
    )
    db.add(new_version)
    await db.flush()

    job = IngestionJobs(
        document_id=new_doc.id,
        version_id=new_version.id,
        job_type="WEBSITE_URL",
        source_url=req.url,
        status=JobStatus.QUEUED,
        job_metadata={"source_url": req.url},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Enqueue background task
    queue_ingestion_job(job.id, "extract")

    return ApiResponse(
        success=True,
        data={
            "document_id": str(new_doc.id),
            "version_id": str(new_version.id),
            "job_id": str(job.id),
            "status": DocumentStatus.UPLOADED.value,
            "message": "Website URL ingestion queued. Background worker will scrape and structure content.",
        },
    )


# ── 3. SAFE VERSION REPLACEMENT ──────────────────────────────────────────────

@router.post("/documents/{doc_id}/replace", response_model=ApiResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Admin Documents"])
async def replace_document_version(
    doc_id: uuid.UUID,
    file: UploadFile = File(...),
    change_summary: str = Form(...),
    valid_from: Optional[str] = Form(None),
    valid_until: Optional[str] = Form(None),
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.CONTENT_APPROVER])),
    db: AsyncSession = Depends(get_db),
):
    """Safely stages a new document version for an existing document without deactivating
    the currently active version until processing, review, and indexing pass successfully.
    """
    doc = await db.get(Documents, doc_id)
    if not doc:
        raise NotFoundError(f"Document with ID '{doc_id}' not found.")

    file_bytes = await file.read()
    pdf_service.validate_pdf_content(file_bytes)
    checksum = calculate_sha256(file_bytes)

    # Determine next version number
    res_versions = await db.execute(
        select(func.max(DocumentVersions.version_number)).where(DocumentVersions.document_id == doc_id)
    )
    max_ver = res_versions.scalar() or 0
    next_version = max_ver + 1

    storage_path = pdf_service.generate_safe_storage_path(doc.id, version_number=next_version, original_filename=file.filename or "replacement.pdf")
    storage_path.write_bytes(file_bytes)

    # Stage new version in UPLOADED state (active version remains active and untouched!)
    new_version = DocumentVersions(
        document_id=doc.id,
        version_number=next_version,
        file_name=file.filename or f"replacement_v{next_version}.pdf",
        storage_path=str(storage_path),
        mime_type="application/pdf",
        file_size_bytes=len(file_bytes),
        checksum_sha256=checksum,
        status=DocumentStatus.UPLOADED,
        change_summary=change_summary,
        valid_from=_parse_date(valid_from),
        valid_until=_parse_date(valid_until),
        created_by_id=current_user.id,
    )
    db.add(new_version)
    await db.flush()

    job = IngestionJobs(
        document_id=doc.id,
        version_id=new_version.id,
        job_type="PDF_UPLOAD",
        status=JobStatus.QUEUED,
        job_metadata={"action": "REPLACEMENT", "version_number": next_version},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    queue_ingestion_job(job.id, "extract")

    return ApiResponse(
        success=True,
        data={
            "document_id": str(doc.id),
            "version_id": str(new_version.id),
            "version_number": next_version,
            "job_id": str(job.id),
            "status": DocumentStatus.UPLOADED.value,
            "message": f"Version {next_version} staged safely. Prior active version remains online until approved.",
        },
    )


# ── 4. TRACK INGESTION JOBS ──────────────────────────────────────────────────

@router.get("/documents/jobs/{job_id}", response_model=ApiResponse, tags=["Admin Documents"])
async def get_job_status(
    job_id: uuid.UUID,
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DEPARTMENT_STAFF, UserRole.VIEWER, UserRole.CONTENT_APPROVER, UserRole.AUDITOR])),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves execution status, retry count, and errors for background ingestion jobs."""
    job = await db.get(IngestionJobs, job_id)
    if not job:
        raise NotFoundError(f"Ingestion job '{job_id}' not found.")

    return ApiResponse(
        success=True,
        data={
            "id": str(job.id),
            "document_id": str(job.document_id) if job.document_id else None,
            "version_id": str(job.version_id) if job.version_id else None,
            "job_type": job.job_type,
            "status": job.status.value,
            "retry_count": job.retry_count,
            "max_retries": job.max_retries,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        },
    )


# ── 5. PREVIEW EXTRACTED TEXT ────────────────────────────────────────────────

@router.get("/documents/{doc_id}/versions/{version_id}/preview", response_model=ApiResponse, tags=["Admin Documents"])
async def preview_document_version(
    doc_id: uuid.UUID,
    version_id: uuid.UUID,
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DEPARTMENT_STAFF, UserRole.VIEWER, UserRole.CONTENT_APPROVER])),
    db: AsyncSession = Depends(get_db),
):
    """Provides extracted text preview, page count, and status for administrator review."""
    ver = await db.get(DocumentVersions, version_id)
    if not ver or ver.document_id != doc_id:
        raise NotFoundError(f"Document version '{version_id}' not found.")

    doc = await db.get(Documents, doc_id)
    if doc:
        check_department_scope(current_user, doc.department_id)

    return ApiResponse(
        success=True,
        data={
            "document_id": str(ver.document_id),
            "version_id": str(ver.id),
            "version_number": ver.version_number,
            "status": ver.status.value,
            "file_name": ver.file_name,
            "page_count": ver.page_count,
            "chunk_count": ver.chunk_count,
            "change_summary": ver.change_summary,
            "extracted_text_preview": ver.extracted_text_preview or "Extraction in progress or no text available.",
            "valid_from": ver.valid_from.isoformat() if ver.valid_from else None,
            "valid_until": ver.valid_until.isoformat() if ver.valid_until else None,
            "created_at": ver.created_at.isoformat(),
        },
    )


# ── 6. APPROVE VERSION & TRIGGER INDEXING ────────────────────────────────────

@router.post("/documents/{doc_id}/versions/{version_id}/approve", response_model=ApiResponse, tags=["Admin Documents"])
async def approve_document_version(
    doc_id: uuid.UUID,
    version_id: uuid.UUID,
    req: Optional[DocumentApprovalRequest] = None,
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.CONTENT_APPROVER])),
    db: AsyncSession = Depends(get_db),
):
    """Allows authorized staff to approve extracted content, transitioning the version
    to APPROVED and launching background pgvector indexing.
    """
    ver = await db.get(DocumentVersions, version_id)
    if not ver or ver.document_id != doc_id:
        raise NotFoundError(f"Document version '{version_id}' not found.")

    if ver.status in (DocumentStatus.ACTIVE, DocumentStatus.PUBLISHED):
        return ApiResponse(success=True, message="Document version is already active.")

    ver.status = DocumentStatus.APPROVED
    ver.approved_by_id = current_user.id
    ver.approved_at = datetime.datetime.now(datetime.timezone.utc)
    ver.updated_at = datetime.datetime.now(datetime.timezone.utc)

    # Create background indexing job
    job = IngestionJobs(
        document_id=doc_id,
        version_id=version_id,
        job_type="INDEXING",
        status=JobStatus.QUEUED,
        job_metadata={"approved_by": str(current_user.id)},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Launch background embedding and activation
    queue_ingestion_job(job.id, "index")

    return ApiResponse(
        success=True,
        data={
            "document_id": str(doc_id),
            "version_id": str(version_id),
            "status": DocumentStatus.APPROVED.value,
            "indexing_job_id": str(job.id),
            "message": "Version approved. Pgvector embedding and activation running in background.",
        },
    )


# ── 7. REJECT VERSION ────────────────────────────────────────────────────────

@router.post("/documents/{doc_id}/versions/{version_id}/reject", response_model=ApiResponse, tags=["Admin Documents"])
async def reject_document_version(
    doc_id: uuid.UUID,
    version_id: uuid.UUID,
    req: DocumentRejectRequest,
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.CONTENT_APPROVER])),
    db: AsyncSession = Depends(get_db),
):
    """Allows staff to reject extracted text. Marks the version as FAILED."""
    ver = await db.get(DocumentVersions, version_id)
    if not ver or ver.document_id != doc_id:
        raise NotFoundError(f"Document version '{version_id}' not found.")

    ver.status = DocumentStatus.FAILED
    ver.change_summary = f"REJECTED: {req.reason}"
    ver.updated_at = datetime.datetime.now(datetime.timezone.utc)

    doc = await db.get(Documents, doc_id)
    if doc and doc.active_version_id is None:
        doc.status = DocumentStatus.FAILED

    await db.commit()
    return ApiResponse(success=True, message=f"Document version {ver.version_number} rejected.")


# ── 8. ARCHIVE DOCUMENT ──────────────────────────────────────────────────────

@router.post("/documents/{doc_id}/archive", response_model=ApiResponse, tags=["Admin Documents"])
async def archive_document(
    doc_id: uuid.UUID,
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.CONTENT_APPROVER])),
    db: AsyncSession = Depends(get_db),
):
    """Archives document and all its versions, instantly removing it from chatbot retrieval."""
    doc = await db.get(Documents, doc_id)
    if not doc:
        raise NotFoundError(f"Document '{doc_id}' not found.")

    doc.status = DocumentStatus.ARCHIVED
    doc.updated_at = datetime.datetime.now(datetime.timezone.utc)

    # Archive all associated versions
    res_versions = await db.execute(select(DocumentVersions).where(DocumentVersions.document_id == doc_id))
    for v in res_versions.scalars().all():
        v.status = DocumentStatus.ARCHIVED
        v.updated_at = datetime.datetime.now(datetime.timezone.utc)

    await db.commit()
    return ApiResponse(success=True, message="Document and all associated versions archived.")


# ── 9. SECURE FILE DOWNLOAD ──────────────────────────────────────────────────

@router.get("/documents/{doc_id}/download", tags=["Admin Documents"])
async def download_document_file(
    doc_id: uuid.UUID,
    version_number: Optional[int] = None,
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DEPARTMENT_STAFF, UserRole.VIEWER, UserRole.CONTENT_APPROVER, UserRole.AUDITOR])),
    db: AsyncSession = Depends(get_db),
):
    """Securely downloads uploaded PDF with strict Content-Type, Content-Disposition: attachment,
    and X-Content-Type-Options: nosniff headers to prevent executable execution.
    """
    doc = await db.get(Documents, doc_id)
    if not doc:
        raise NotFoundError(f"Document '{doc_id}' not found.")
    check_department_scope(current_user, doc.department_id)

    query = select(DocumentVersions).where(DocumentVersions.document_id == doc_id)
    if version_number:
        query = query.where(DocumentVersions.version_number == version_number)
    else:
        query = query.order_by(DocumentVersions.version_number.desc())

    res = await db.execute(query)
    ver = res.scalars().first()
    if not ver:
        raise NotFoundError(f"File for document '{doc_id}' not found.")

    file_path = pathlib.Path(ver.storage_path)
    if not file_path.exists():
        raise NotFoundError("Stored document file missing on disk.")

    safe_download_name = f"document_{doc_id}_v{ver.version_number}.pdf"

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=safe_download_name,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_download_name}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


# ── 10. LIST DOCUMENTS & DETAILS ─────────────────────────────────────────────

@router.get("/documents", response_model=ApiResponse, tags=["Admin Documents"])
async def list_documents(
    status: Optional[str] = None,
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DEPARTMENT_STAFF, UserRole.VIEWER, UserRole.CONTENT_APPROVER, UserRole.AUDITOR])),
    db: AsyncSession = Depends(get_db),
):
    """Lists institutional documents with optional status filtering."""
    query = (
        select(Documents)
        .options(
            selectinload(Documents.department),
            selectinload(Documents.academic_year),
            selectinload(Documents.active_version),
            selectinload(Documents.versions),
        )
    )
    if current_user.role == UserRole.DEPARTMENT_STAFF and current_user.department_id:
        query = query.where(Documents.department_id == current_user.department_id)

    if status and status != "ALL":
        query = query.where(Documents.status == status)
    result = await db.execute(query.order_by(Documents.created_at.desc()).limit(100))
    docs = result.scalars().all()

    data = [
        {
            "id": str(d.id),
            "title": d.title,
            "file_name": d.file_name,
            "department": d.department.name if d.department else "General Administration",
            "department_code": d.department.code if d.department else "GENERAL",
            "academic_year": d.academic_year.code if d.academic_year else "2025-2026",
            "version_number": d.version_number,
            "active_version_id": str(d.active_version_id) if d.active_version_id else None,
            "status": d.status.value,
            "file_size_bytes": d.file_size_bytes,
            "chunk_count": d.active_version.chunk_count if d.active_version else (d.versions[0].chunk_count if d.versions else 0),
            "page_count": d.active_version.page_count if d.active_version else (d.versions[0].page_count if d.versions else 0),
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]
    return ApiResponse(success=True, data=data)


@router.get("/documents/{doc_id}", response_model=ApiResponse, tags=["Admin Documents"])
async def get_document_detail(
    doc_id: uuid.UUID,
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DEPARTMENT_STAFF, UserRole.VIEWER, UserRole.CONTENT_APPROVER, UserRole.AUDITOR])),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves document detail and list of all historical versions."""
    res = await db.execute(
        select(Documents)
        .options(selectinload(Documents.versions))
        .where(Documents.id == doc_id)
    )
    doc = res.scalars().first()
    if not doc:
        raise NotFoundError(f"Document '{doc_id}' not found.")
    check_department_scope(current_user, doc.department_id)

    versions_data = [
        {
            "id": str(v.id),
            "version_number": v.version_number,
            "file_name": v.file_name,
            "status": v.status.value,
            "page_count": v.page_count,
            "chunk_count": v.chunk_count,
            "checksum_sha256": v.checksum_sha256,
            "valid_from": v.valid_from.isoformat() if v.valid_from else None,
            "valid_until": v.valid_until.isoformat() if v.valid_until else None,
            "change_summary": v.change_summary,
            "created_at": v.created_at.isoformat(),
            "approved_at": v.approved_at.isoformat() if v.approved_at else None,
        }
        for v in sorted(doc.versions, key=lambda x: x.version_number, reverse=True)
    ]

    return ApiResponse(
        success=True,
        data={
            "id": str(doc.id),
            "title": doc.title,
            "file_name": doc.file_name,
            "version_number": doc.version_number,
            "active_version_id": str(doc.active_version_id) if doc.active_version_id else None,
            "status": doc.status.value,
            "file_size_bytes": doc.file_size_bytes,
            "checksum_sha256": doc.checksum_sha256,
            "created_at": doc.created_at.isoformat(),
            "versions": versions_data,
        },
    )
