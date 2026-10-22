#!/usr/bin/env python3
# ==============================================================================
# Ingest Demonstration PDF into PostgreSQL pgvector Store
# ==============================================================================
import asyncio
import hashlib
import os
import pathlib
import sys

# Ensure backend Service is on path
ROOT_DIR = pathlib.Path(__file__).parent.parent
SERVICE_DIR = ROOT_DIR / "backend" / "Services" / "HelpdeskService"
sys.path.insert(0, str(SERVICE_DIR))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from configs.base_config import BaseConfig
from models.models import (
    AcademicYears,
    Departments,
    DocumentChunks,
    DocumentStatus,
    Documents,
    DocumentVersions,
    Users,
    UserRole,
)
from resources.pdfService import pdf_service
from resources.aiService import get_embedding_provider
from resources.utils import hash_password, calculate_sha256

PDF_PATH = ROOT_DIR / "backend" / "storage" / "demo_college_regulations_2025_2026.pdf"


async def ingest():
    print(f"=== [1/5] Checking Demonstration PDF at: {PDF_PATH} ===")
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found at {PDF_PATH}. Run scripts/generate_demo_pdf.py first.")

    content = PDF_PATH.read_bytes()
    checksum = calculate_sha256(content)
    file_size = len(content)
    print(f"File size: {file_size} bytes | SHA-256: {checksum[:12]}...")

    engine = create_async_engine(BaseConfig.DB_URI, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as db:
        print("=== [2/5] Resolving Master Records (Academic Year, Dept, Admin) ===")
        # 1. Academic Year
        ay_res = await db.execute(select(AcademicYears).where(AcademicYears.code == "2025-2026"))
        ay = ay_res.scalars().first()
        if not ay:
            from datetime import date
            ay = AcademicYears(code="2025-2026", start_date=date(2025, 6, 1), end_date=date(2026, 5, 31), is_current=True)
            db.add(ay)
            await db.commit()
            await db.refresh(ay)

        # 2. Department
        dept_res = await db.execute(select(Departments).where(Departments.code == "ACA"))
        dept = dept_res.scalars().first()
        if not dept:
            dept = Departments(code="ACA", name="Academic Affairs", contact_email="academics@college.edu", is_active=True)
            db.add(dept)
            await db.commit()
            await db.refresh(dept)

        # 3. Super Admin User
        admin_res = await db.execute(select(Users).where(Users.email == "admin@college.edu"))
        admin_user = admin_res.scalars().first()
        if not admin_user:
            admin_user = Users(
                email="admin@college.edu",
                full_name="System Administrator",
                password_hash=hash_password("DevAdminSecret123#!"),
                role=UserRole.SUPER_ADMIN,
                is_active=True,
            )
            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)

        print("=== [3/5] Extracting Pages and Creating Structure-Aware Chunks ===")
        pages = pdf_service.extract_pages(content)
        print(f"Extracted {len(pages)} pages.")

        doc_title = "[DEMONSTRATION SAMPLE] St. Jude College Academic & Campus Regulations 2025-2026"
        chunks_data = pdf_service.chunk_document(
            pages=pages,
            document_title=doc_title,
            academic_year="2025-2026",
            department="Academic Affairs",
        )
        print(f"Generated {len(chunks_data)} semantic chunks.")

        print("=== [4/5] Generating Vector Embeddings ===")
        embedder = get_embedding_provider()
        chunk_texts = [c.content for c in chunks_data]
        embeddings = await embedder.get_embeddings_batch(chunk_texts)
        print(f"Generated {len(embeddings)} embedding vectors (1536 dim).")

        print("=== [5/5] Persisting Document and Vector Chunks to Database ===")
        # Remove any previous version with the same checksum or filename
        existing_doc = await db.execute(select(Documents).where(Documents.file_name == "demo_college_regulations_2025_2026.pdf"))
        doc = existing_doc.scalars().first()
        if doc:
            await db.delete(doc)
            await db.commit()

        # Create Document record
        new_doc = Documents(
            title=doc_title,
            file_name="demo_college_regulations_2025_2026.pdf",
            storage_path=str(PDF_PATH),
            mime_type="application/pdf",
            file_size_bytes=file_size,
            checksum_sha256=checksum,
            version_number=1,
            status=DocumentStatus.PUBLISHED,
            document_type="REGULATION",
            language_code="en",
            academic_year_id=ay.id,
            department_id=dept.id,
            uploaded_by_id=admin_user.id,
            approved_by_id=admin_user.id,
        )
        db.add(new_doc)
        await db.commit()
        await db.refresh(new_doc)

        # Create DocumentVersion record
        new_version = DocumentVersions(
            document_id=new_doc.id,
            version_number=1,
            file_name="demo_college_regulations_2025_2026.pdf",
            storage_path=str(PDF_PATH),
            mime_type="application/pdf",
            file_size_bytes=file_size,
            checksum_sha256=checksum,
            status=DocumentStatus.PUBLISHED,
            document_type="REGULATION",
            language_code="en",
            change_summary="Initial demonstration regulations",
            page_count=len(pages),
            chunk_count=len(chunks_data),
            created_by_id=admin_user.id,
            approved_by_id=admin_user.id,
        )
        db.add(new_version)
        await db.commit()
        await db.refresh(new_version)

        new_doc.active_version_id = new_version.id
        await db.commit()

        # Store Chunks
        for idx, (chunk_info, embedding_vector) in enumerate(zip(chunks_data, embeddings)):
            chunk_rec = DocumentChunks(
                document_id=new_doc.id,
                version_id=new_version.id,
                chunk_index=chunk_info.chunk_index,
                page_number=chunk_info.page_number,
                content=chunk_info.content,
                token_count=chunk_info.token_count,
                embedding=embedding_vector,
                chunk_metadata=chunk_info.metadata,
            )
            db.add(chunk_rec)

        await db.commit()

        # Verify chunk count
        count_res = await db.execute(text("SELECT count(*) FROM document_chunks WHERE document_id = :did;"), {"did": new_doc.id})
        count = count_res.scalar()
        print(f"Successfully ingested and indexed {count} chunks for document: {new_doc.title}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(ingest())
