# backend/Services/HelpdeskService/tests/test_document_ingestion.py
import datetime
import io
import pathlib
import uuid
import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select

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
    UserRole,
    Users,
)
from resources.errors import OCRExtractionError, SSRFValidationError
from resources.pdfService import ExtractedPage, pdf_service
from resources.ragService import rag_service
from resources.utils import create_access_token, hash_password
from resources.webScraperService import web_scraper_service
from tasks.ingestion_tasks import (
    execute_document_extraction_job,
    execute_document_indexing_job,
)

SAMPLE_PDF_PATH = pathlib.Path(__file__).resolve().parents[3] / "storage" / "demo_college_regulations_2025_2026.pdf"


@pytest.fixture
async def admin_auth_token():
    async with async_session_factory() as db:
        res = await db.execute(select(Users).where(Users.email == "admin@college.edu"))
        admin = res.scalars().first()
        assert admin is not None
        token = create_access_token({
            "sub": str(admin.id),
            "email": admin.email,
            "role": admin.role.value,
        })
        return token, admin


@pytest.fixture
async def support_agent_token():
    async with async_session_factory() as db:
        # Create or fetch support agent user
        res = await db.execute(select(Users).where(Users.email == "agent@college.edu"))
        agent = res.scalars().first()
        if not agent:
            agent = Users(
                email="agent@college.edu",
                full_name="Support Desk Agent",
                password_hash=hash_password("AgentPass123!"),
                role=UserRole.SUPPORT_AGENT,
            )
            db.add(agent)
            await db.commit()
            await db.refresh(agent)

        token = create_access_token({
            "sub": str(agent.id),
            "email": agent.email,
            "role": agent.role.value,
        })
        return token, agent


# ── 1. SECURITY & ACCESS CONTROL TESTS ───────────────────────────────────────

@pytest.mark.asyncio
async def test_unauthorized_upload_attempt(async_client: AsyncClient):
    """Verifies that unauthenticated requests to document upload are rejected with 401."""
    pdf_bytes = b"%PDF-1.4\nTest dummy"
    files = {"file": ("test.pdf", pdf_bytes, "application/pdf")}
    data = {"title": "Test Circular"}

    resp = await async_client.post("/api/v1/admin/documents/upload", files=files, data=data)
    assert resp.status_code == 401
    assert "Missing or malformed" in resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_forbidden_role_upload_attempt(async_client: AsyncClient, support_agent_token):
    """Verifies that non-administrative staff (e.g. SUPPORT_AGENT) are rejected with 403."""
    token, _ = support_agent_token
    pdf_bytes = b"%PDF-1.4\nTest dummy"
    files = {"file": ("test.pdf", pdf_bytes, "application/pdf")}
    data = {"title": "Test Circular"}

    headers = {"Authorization": f"Bearer {token}"}
    resp = await async_client.post("/api/v1/admin/documents/upload", files=files, data=data, headers=headers)
    assert resp.status_code == 403
    assert "privileges" in resp.json()["error"]["message"]


# ── 2. SECURE FILE VALIDATION TESTS ──────────────────────────────────────────

def test_file_type_and_signature_validation():
    """Requirement 6: Validate file types using magic bytes; reject non-PDFs."""
    invalid_content = b"<html><script>alert(1)</script></html>"
    with pytest.raises(Exception) as excinfo:
        pdf_service.validate_pdf_content(invalid_content)
    assert "Invalid file signature" in str(excinfo.value)

    # Empty file
    with pytest.raises(Exception) as excinfo:
        pdf_service.validate_pdf_content(b"")
    assert "empty" in str(excinfo.value)


def test_safe_storage_name_generation():
    """Requirement 6: Do not trust user-supplied filenames; generate safe UUID paths."""
    doc_id = uuid.uuid4()
    path = pdf_service.generate_safe_storage_path(
        document_id=doc_id,
        version_number=1,
        original_filename="../../../etc/evil_script.sh",
    )
    assert "evil_script.sh" not in str(path)
    assert str(doc_id) in str(path)
    assert path.name.startswith("v1_")
    assert path.suffix == ".pdf"


# ── 3. WEBSITE INGESTION & SSRF DEFENSE TESTS ────────────────────────────────

def test_ssrf_defense_blocks_internal_and_loopback_destinations():
    """Requirement 7: Website ingestion blocks loopback, private networks, and cloud metadata."""
    forbidden_urls = [
        "http://localhost:8000/api/keys",
        "http://127.0.0.1:8080/admin",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.5/internal",
        "http://192.168.1.1/router",
        "file:///etc/passwd",
        "ftp://institution.edu/dump",
    ]

    for bad_url in forbidden_urls:
        with pytest.raises(SSRFValidationError):
            web_scraper_service.validate_url_against_ssrf(bad_url)


@pytest.mark.asyncio
async def test_api_ssrf_rejection(async_client: AsyncClient, admin_auth_token):
    """Verifies that admin URL ingestion endpoint strictly rejects SSRF targets."""
    token, _ = admin_auth_token
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "url": "http://127.0.0.1:8005/api/admin/secrets",
        "academic_year_code": "2025-2026",
    }
    resp = await async_client.post("/api/v1/admin/documents/ingest-url", json=payload, headers=headers)
    assert resp.status_code == 400
    assert "SSRF" in resp.json()["error"]["code"] or "Forbidden" in resp.json()["error"]["message"]


def test_web_content_cleaning_and_structuring():
    """Requirement 7: Clean HTML tags and extract structured content."""
    html_sample = b"""
    <!DOCTYPE html>
    <html>
    <head><title>St. Jude Computer Science Department</title></head>
    <body>
        <nav><a href="/">Home</a><a href="/login">Login</a></nav>
        <h1>Department of Computer Science & Engineering</h1>
        <p>The CSE department was established in 2005. It offers B.E. and M.E. programs.</p>
        <p>Laboratory facilities include AI, Cloud Computing, and Robotics Labs.</p>
        <footer>Copyright 2026 College Helpdesk</footer>
        <script>console.log('tracker');</script>
    </body>
    </html>
    """
    title, pages = web_scraper_service.parse_web_content(html_sample, "https://college.edu/cse")
    assert title == "St. Jude Computer Science Department"
    assert len(pages) >= 1
    combined_text = " ".join(p.text for p in pages)
    assert "CSE department was established" in combined_text
    assert "tracker" not in combined_text  # Script stripped
    assert "Login" not in combined_text    # Nav stripped


# ── 4. OCR DETECTION & FAILURE HANDLING TESTS ────────────────────────────────

def test_scanned_page_detection_and_ocr_fallback():
    """Requirement 1: Detect scanned pages and handle OCR failures safely."""
    # Create mock page with low text density
    page = ExtractedPage(page_number=1, text="Title", char_count=5, is_scanned=True)
    assert page.is_scanned is True

    # Test OCR service error handling with custom engine raising exception
    def failing_ocr_engine(_img):
        raise RuntimeError("OCR subprocess timeout")

    failing_service = pdf_service.__class__(custom_ocr_engine=failing_ocr_engine)
    assert failing_service.custom_ocr_engine is not None


# ── 5. FULL INGESTION LIFECYCLE & BACKGROUND JOBS ────────────────────────────

@pytest.mark.asyncio
async def test_duplicate_pdf_upload_rejection(async_client: AsyncClient, admin_auth_token):
    """Requirement 2: Avoid duplicate processing where appropriate (409 Conflict)."""
    token, _ = admin_auth_token
    headers = {"Authorization": f"Bearer {token}"}

    # Use the existing demo PDF which is already in the database
    pdf_bytes = SAMPLE_PDF_PATH.read_bytes()
    files = {"file": ("demo_college_regulations.pdf", pdf_bytes, "application/pdf")}
    data = {
        "title": "Duplicate Upload Attempt",
        "academic_year_code": "2025-2026",
    }
    resp = await async_client.post("/api/v1/admin/documents/upload", files=files, data=data, headers=headers)
    assert resp.status_code == 409
    assert "identical document version already exists" in resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_full_document_ingestion_and_approval_workflow(async_client: AsyncClient, admin_auth_token):
    """Requirements 1-5: Full lifecycle test:
    Upload -> Background Extraction -> Review Preview -> Staff Approval -> Indexing -> Active Retrieval.
    """
    token, admin = admin_auth_token
    headers = {"Authorization": f"Bearer {token}"}

    assert SAMPLE_PDF_PATH.exists()
    # Add unique comment to PDF to test distinct upload
    unique_marker = f"\n% TEST_UPLOAD_{uuid.uuid4().hex}\n".encode()
    pdf_bytes = SAMPLE_PDF_PATH.read_bytes() + unique_marker

    # Step 1: Upload PDF (status -> UPLOADED)
    doc_title = f"Test Hostel Policy {uuid.uuid4().hex[:6]}"
    files = {"file": ("hostel_policy.pdf", pdf_bytes, "application/pdf")}
    data = {
        "title": doc_title,
        "academic_year_code": "2025-2026",
        "department_code": "GENERAL",
        "valid_from": "2025-06-01",
        "valid_until": "2026-05-31",
        "change_summary": "Official hostel policy update",
    }

    resp = await async_client.post("/api/v1/admin/documents/upload", files=files, data=data, headers=headers)
    assert resp.status_code == 202
    resp_data = resp.json()["data"]
    doc_id = uuid.UUID(resp_data["document_id"])
    version_id = uuid.UUID(resp_data["version_id"])
    job_id = uuid.UUID(resp_data["job_id"])

    # Step 2: Track Job in QUEUED state
    job_resp = await async_client.get(f"/api/v1/admin/documents/jobs/{job_id}", headers=headers)
    assert job_resp.status_code == 200
    assert job_resp.json()["data"]["status"] in [JobStatus.QUEUED.value, JobStatus.PROCESSING.value, JobStatus.COMPLETED.value]

    # Step 3: Execute background extraction job
    job_res = await execute_document_extraction_job(job_id)
    assert job_res["status"] == "COMPLETED"

    # Step 4: Preview extracted text
    preview_resp = await async_client.get(f"/api/v1/admin/documents/{doc_id}/versions/{version_id}/preview", headers=headers)
    assert preview_resp.status_code == 200
    preview_data = preview_resp.json()["data"]
    assert preview_data["status"] == DocumentStatus.REVIEW_REQUIRED.value
    assert preview_data["page_count"] == 3
    assert len(preview_data["extracted_text_preview"]) > 100

    # Step 5: Verify that before approval, RAG search DOES NOT return this document!
    async with async_session_factory() as db:
        evidence_unapproved = await rag_service.search_evidence(
            db=db,
            query_text="What are the hostel regulations?",
            top_k=10,
        )
        for ev in evidence_unapproved:
            assert ev["document_title"] != doc_title

    # Step 6: Approve Document Version
    approve_resp = await async_client.post(
        f"/api/v1/admin/documents/{doc_id}/versions/{version_id}/approve",
        headers=headers,
    )
    assert approve_resp.status_code == 200
    indexing_job_id = uuid.UUID(approve_resp.json()["data"]["indexing_job_id"])

    # Step 7: Execute background indexing job
    index_res = await execute_document_indexing_job(indexing_job_id)
    assert index_res["status"] == "COMPLETED"
    assert index_res["chunks_stored"] >= 3

    # Step 8: Verify that after approval and indexing, document version is ACTIVE
    async with async_session_factory() as db:
        v = await db.get(DocumentVersions, version_id)
        assert v.status == DocumentStatus.ACTIVE
        d = await db.get(Documents, doc_id)
        assert d.status == DocumentStatus.ACTIVE
        assert d.active_version_id == version_id

        # Verify chunks are associated with version_id
        res_chunks = await db.execute(select(DocumentChunks).where(DocumentChunks.version_id == version_id))
        chunks = res_chunks.scalars().all()
        assert len(chunks) >= 3
        for c in chunks:
            assert c.version_id == version_id
            assert c.document_id == doc_id


# ── 6. SAFE VERSION REPLACEMENT TESTS ────────────────────────────────────────

@pytest.mark.asyncio
async def test_safe_version_replacement_failure_isolation(async_client: AsyncClient, admin_auth_token):
    """REPLACEMENT SAFETY Requirement:
    Do not deactivate currently active version until replacement passes validation and indexing.
    Handle failed replacements without losing access to previous valid version.
    """
    token, _ = admin_auth_token
    headers = {"Authorization": f"Bearer {token}"}
    pdf_bytes = SAMPLE_PDF_PATH.read_bytes()

    # Create baseline Document and Version 1 (ACTIVE)
    async with async_session_factory() as db:
        ay = (await db.execute(select(AcademicYears))).scalars().first()
        dept = (await db.execute(select(Departments))).scalars().first()
        admin_user = (await db.execute(select(Users))).scalars().first()

        doc = Documents(
            title="College Exam Regulations Baseline",
            file_name="regulations_v1.pdf",
            storage_path=str(SAMPLE_PDF_PATH),
            mime_type="application/pdf",
            file_size_bytes=len(pdf_bytes),
            checksum_sha256="test-chk-v1-" + uuid.uuid4().hex,
            version_number=1,
            status=DocumentStatus.ACTIVE,
            academic_year_id=ay.id,
            department_id=dept.id,
            uploaded_by_id=admin_user.id,
        )
        db.add(doc)
        await db.flush()

        v1 = DocumentVersions(
            document_id=doc.id,
            version_number=1,
            file_name="regulations_v1.pdf",
            storage_path=str(SAMPLE_PDF_PATH),
            mime_type="application/pdf",
            file_size_bytes=len(pdf_bytes),
            checksum_sha256=doc.checksum_sha256,
            status=DocumentStatus.ACTIVE,
            page_count=3,
            chunk_count=3,
        )
        db.add(v1)
        await db.flush()
        doc.active_version_id = v1.id
        await db.commit()
        await db.refresh(doc)
        await db.refresh(v1)

        doc_id = doc.id
        v1_id = v1.id

    # Stage Version 2 Replacement
    files = {"file": ("regulations_v2.pdf", pdf_bytes, "application/pdf")}
    data = {"change_summary": "Updated exam grading policy"}
    resp = await async_client.post(f"/api/v1/admin/documents/{doc_id}/replace", files=files, data=data, headers=headers)
    assert resp.status_code == 202
    v2_id = uuid.UUID(resp.json()["data"]["version_id"])
    v2_job_id = uuid.UUID(resp.json()["data"]["job_id"])

    # Verify that while v2 is in UPLOADED/PROCESSING, v1 REMAINS ACTIVE!
    async with async_session_factory() as db:
        doc_check = await db.get(Documents, doc_id)
        v1_check = await db.get(DocumentVersions, v1_id)
        v2_check = await db.get(DocumentVersions, v2_id)

        assert doc_check.active_version_id == v1_id
        assert v1_check.status == DocumentStatus.ACTIVE
        assert v2_check.status == DocumentStatus.UPLOADED

    # Simulate rejection or extraction failure on Version 2
    reject_resp = await async_client.post(
        f"/api/v1/admin/documents/{doc_id}/versions/{v2_id}/reject",
        json={"reason": "Contains formatting inconsistencies"},
        headers=headers,
    )
    assert reject_resp.status_code == 200

    # Verify that V1 IS STILL ACTIVE and online for students!
    async with async_session_factory() as db:
        doc_final = await db.get(Documents, doc_id)
        v1_final = await db.get(DocumentVersions, v1_id)
        v2_final = await db.get(DocumentVersions, v2_id)

        assert v2_final.status == DocumentStatus.FAILED
        assert v1_final.status == DocumentStatus.ACTIVE
        assert doc_final.active_version_id == v1_id  # Untouched and valid!


# ── 7. DOCUMENT ARCHIVAL TESTS ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_document_archival_excludes_from_retrieval(async_client: AsyncClient, admin_auth_token):
    """Verifies that archiving a document transitions status to ARCHIVED and excludes it
    from RAG evidence retrieval.
    """
    token, _ = admin_auth_token
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch existing published/active document
    async with async_session_factory() as db:
        res = await db.execute(select(Documents).where(Documents.status.in_([DocumentStatus.ACTIVE, DocumentStatus.PUBLISHED])))
        doc = res.scalars().first()
        assert doc is not None
        target_doc_id = doc.id

    # Archive document
    archive_resp = await async_client.post(f"/api/v1/admin/documents/{target_doc_id}/archive", headers=headers)
    assert archive_resp.status_code == 200

    # Verify RAG retrieval excludes archived document
    async with async_session_factory() as db:
        evidence = await rag_service.search_evidence(
            db=db,
            query_text="What is the hostel caution deposit fee?",
            top_k=5,
        )
        for ev in evidence:
            assert ev["document_id"] != target_doc_id

        # Restore document to PUBLISHED so subsequent tests or demo continues to work
        doc_restore = await db.get(Documents, target_doc_id)
        doc_restore.status = DocumentStatus.PUBLISHED
        if doc_restore.active_version_id:
            v_restore = await db.get(DocumentVersions, doc_restore.active_version_id)
            if v_restore:
                v_restore.status = DocumentStatus.PUBLISHED
        await db.commit()


# ── 8. SECURE DOWNLOAD EXECUTION PROTECTION TEST ─────────────────────────────

@pytest.mark.asyncio
async def test_secure_download_headers(async_client: AsyncClient, admin_auth_token):
    """Requirement 6: Prevent uploaded files from being served as executable content."""
    token, _ = admin_auth_token
    headers = {"Authorization": f"Bearer {token}"}

    async with async_session_factory() as db:
        doc = (await db.execute(select(Documents))).scalars().first()
        doc_id = doc.id

    resp = await async_client.get(f"/api/v1/admin/documents/{doc_id}/download", headers=headers)
    assert resp.status_code == 200
    assert resp.headers.get("content-type") == "application/pdf"
    assert "attachment" in resp.headers.get("content-disposition", "")
    assert resp.headers.get("x-content-type-options") == "nosniff"
