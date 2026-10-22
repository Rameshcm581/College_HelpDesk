#!/usr/bin/env python3
# ==============================================================================
# Ingest Official Tamil Circular for Multilingual RAG Testing
# ==============================================================================
import asyncio
import hashlib
import os
import pathlib
import sys
import uuid

ROOT_DIR = pathlib.Path(__file__).parent.parent
SERVICE_DIR = ROOT_DIR / "backend" / "Services" / "HelpdeskService"
sys.path.insert(0, str(SERVICE_DIR))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
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
from resources.aiService import get_embedding_provider
from resources.utils import hash_password, calculate_sha256

TAMIL_DOC_TITLE = "செயின்ட் ஜூட் பொறியியல் கல்லூரி - கல்வி உதவித்தொகை மற்றும் கட்டண சலுகை சுற்றறிக்கை 2025-2026"
FILE_NAME = "st_jude_scholarship_circular_2025_2026_ta.pdf"

TAMIL_CONTENT_PAGE_1 = """செயின்ட் ஜூட் பொறியியல் மற்றும் தொழில்நுட்பக் கல்லூரி
மாணவர் நலன் மற்றும் கல்வி உதவித்தொகை பிரிவு (2025–2026)
அதிகாரப்பூர்வ சுற்றறிக்கை எண்: SJCET/SCH/2025/04

1. முதல் தலைமுறை பட்டதாரி கல்வி உதவித்தொகை (First Graduate Scholarship):
குடும்பத்தில் முதல் தலைமுறை பட்டதாரி மாணவ மாணவியருக்கு அரசு விதிகளின்படி ஆண்டிற்கு ரூ.25,000 (₹25,000) கல்விக் கட்டண சலுகை வழங்கப்படுகிறது. இச்சலுகை பெற தகுதி வாய்ந்த வருவாய் வட்டாட்சியர் (Tahsildar) வழங்கிய அதிகாரப்பூர்வ முதல் தலைமுறை பட்டதாரி சான்றிதழ் சேர்க்கையின் போது சமர்ப்பிக்கப்பட வேண்டும்.

2. விளையாட்டு வீரர்களுக்கான கட்டண சலுகை (Sports Quota Concession):
மாநில அளவிலான விளையாட்டுப் போட்டிகளில் தங்கம் வென்ற மாணவ விளையாட்டு வீரர்களுக்கு 100% தங்கும் விடுதி கட்டண விலக்கு மற்றும் 50% கல்விக் கட்டண விலக்கு அளிக்கப்படுகிறது. தேசிய அளவில் பதக்கம் வென்றவர்களுக்கு முழு கட்டண விலக்கு (100% Fee Waiver) அளிக்கப்படும்.

3. விண்ணப்பிக்கும் கடைசி தேதி மற்றும் அலுவலகம்:
கல்வி உதவித்தொகை மற்றும் கட்டண சலுகைக்கான விண்ணப்பங்களை சமர்ப்பிக்க கடைசி நாள் ஆகஸ்ட் 25, 2025 (August 25, 2025). பூர்த்தி செய்த விண்ணப்பப் படிவங்களை முதன்மை வளாக கட்டடம், அறை எண் 105 இல் உள்ள மாணவர் நல அலுவலகத்தில் காலை 10:00 மணி முதல் மாலை 04:00 மணிக்குள் சமர்ப்பிக்க வேண்டும். தாமதமாக வரும் விண்ணப்பங்கள் ஏற்றுக்கொள்ளப்பட மாட்டாது."""


async def ingest_tamil_circular():
    print("=== Ingesting Tamil Circular Document ===")
    raw_bytes = TAMIL_CONTENT_PAGE_1.encode("utf-8")
    checksum = hashlib.sha256(raw_bytes).hexdigest()
    file_size = len(raw_bytes)

    engine = create_async_engine(BaseConfig.DB_URI, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as db:
        # 1. Resolve Academic Year
        ay_res = await db.execute(select(AcademicYears).where(AcademicYears.code == "2025-2026"))
        ay = ay_res.scalars().first()
        if not ay:
            from datetime import date
            ay = AcademicYears(code="2025-2026", start_date=date(2025, 6, 1), end_date=date(2026, 5, 31), is_current=True)
            db.add(ay)
            await db.commit()
            await db.refresh(ay)

        # 2. Resolve Department
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

        # 4. Remove previous version if exists
        existing_doc = await db.execute(select(Documents).where(Documents.file_name == FILE_NAME))
        doc = existing_doc.scalars().first()
        if doc:
            await db.delete(doc)
            await db.commit()

        # 5. Create Documents record
        new_doc = Documents(
            title=TAMIL_DOC_TITLE,
            file_name=FILE_NAME,
            storage_path=f"storage/{FILE_NAME}",
            mime_type="application/pdf",
            file_size_bytes=file_size,
            checksum_sha256=checksum,
            version_number=1,
            status=DocumentStatus.PUBLISHED,
            document_type="CIRCULAR",
            language_code="ta",
            academic_year_id=ay.id,
            department_id=dept.id,
            uploaded_by_id=admin_user.id,
            approved_by_id=admin_user.id,
        )
        db.add(new_doc)
        await db.commit()
        await db.refresh(new_doc)

        # 6. Create DocumentVersions record
        new_version = DocumentVersions(
            document_id=new_doc.id,
            version_number=1,
            file_name=FILE_NAME,
            storage_path=f"storage/{FILE_NAME}",
            mime_type="application/pdf",
            file_size_bytes=file_size,
            checksum_sha256=checksum,
            status=DocumentStatus.PUBLISHED,
            document_type="CIRCULAR",
            language_code="ta",
            change_summary="Official Tamil Circular on Scholarships and Fee Concessions",
            page_count=1,
            chunk_count=1,
            created_by_id=admin_user.id,
            approved_by_id=admin_user.id,
        )
        db.add(new_version)
        await db.commit()
        await db.refresh(new_version)

        new_doc.active_version_id = new_version.id
        await db.commit()

        # 7. Generate embedding and chunk
        embedder = get_embedding_provider()
        embeddings = await embedder.get_embeddings_batch([TAMIL_CONTENT_PAGE_1])

        chunk_rec = DocumentChunks(
            document_id=new_doc.id,
            version_id=new_version.id,
            chunk_index=0,
            page_number=1,
            content=TAMIL_CONTENT_PAGE_1,
            token_count=len(TAMIL_CONTENT_PAGE_1.split()),
            embedding=embeddings[0],
            chunk_metadata={
                "document_title": TAMIL_DOC_TITLE,
                "academic_year": "2025-2026",
                "department": "Academic Affairs",
                "page": 1,
                "language": "ta",
            },
        )
        db.add(chunk_rec)
        await db.commit()
        print(f"Successfully ingested Tamil circular: {new_doc.title} (ID: {new_doc.id})")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(ingest_tamil_circular())
