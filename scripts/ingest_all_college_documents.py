#!/usr/bin/env python3
"""
========================================================================================
Comprehensive College Documents Ingestion & RAG Verification Pipeline
St. Jude College of Engineering & Technology (Autonomous)
========================================================================================
Feeds all 12 institutional policy documents and the Master Compendium into the
PostgreSQL 16 + pgvector database and triggers automatic tsvector indexing.
Performs verification queries to prove grounded answers with citations.
"""

import asyncio
import hashlib
import os
import pathlib
import sys
import uuid
import datetime

# Setup import paths
ROOT_DIR = pathlib.Path(__file__).parent.parent
SERVICE_DIR = ROOT_DIR / "backend" / "Services" / "HelpdeskService"
sys.path.insert(0, str(SERVICE_DIR))

from sqlalchemy import select, text, delete
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
from resources.aiService import get_embedding_provider, get_llm_provider
from resources.ragService import RAGOrchestrationService
from resources.utils import hash_password, calculate_sha256

PDF_DIR = ROOT_DIR / "college_documents_pdf"

# Department definitions mapping to institutional document domains
DEPARTMENTS_CONFIG = [
    {"code": "ACA", "name": "Academic Affairs", "contact_email": "academics@stjude.edu.in"},
    {"code": "ADM", "name": "Admissions & Finance", "contact_email": "admissions@stjude.edu.in"},
    {"code": "COE", "name": "Controller of Examinations", "contact_email": "coe@stjude.edu.in"},
    {"code": "HST", "name": "Hostel Administration", "contact_email": "hostel@stjude.edu.in"},
    {"code": "SWO", "name": "Student Welfare Office", "contact_email": "welfare@stjude.edu.in"},
    {"code": "CDC", "name": "Career Development Centre", "contact_email": "placements@stjude.edu.in"},
    {"code": "DSC", "name": "Campus Discipline & Security", "contact_email": "discipline@stjude.edu.in"},
    {"code": "ICC", "name": "Internal Complaints Committee", "contact_email": "icc@stjude.edu.in"},
    {"code": "LIB", "name": "Central Library", "contact_email": "library@stjude.edu.in"},
    {"code": "SGR", "name": "Student Grievance Redressal", "contact_email": "grievance@stjude.edu.in"},
    {"code": "HLT", "name": "Health & Campus Amenities", "contact_email": "health@stjude.edu.in"},
    {"code": "ACT", "name": "Student Activities & Sports", "contact_email": "activities@stjude.edu.in"},
    {"code": "GEN", "name": "General Administration", "contact_email": "admin@stjude.edu.in"},
]

# Mapping of file names to metadata
DOCUMENT_METADATA = {
    "00_master_college_handbook_compendium_2025_2026.pdf": {
        "title": "St. Jude College Official Master Handbook & Compendium (2025–2026)",
        "dept_code": "GEN",
        "doc_type": "COMPENDIUM",
        "summary": "Master administrative handbook containing all institutional regulations and policies"
    },
    "01_academic_regulations_2025_2026.pdf": {
        "title": "Academic Regulations & Curriculum Framework (CBCS) 2025–2026",
        "dept_code": "ACA",
        "doc_type": "REGULATION",
        "summary": "Degree credit requirements, 75% attendance rule, condonation fees, and grading scale"
    },
    "02_admissions_and_fee_structure_2025_2026.pdf": {
        "title": "Admissions, Annual Fee Schedule & UGC Refund Policy (2025–2026)",
        "dept_code": "ADM",
        "doc_type": "FEE_STRUCTURE",
        "summary": "Tuition fees, quotas, payment deadlines, late fine slabs, and UGC fee refund rules"
    },
    "03_examinations_and_evaluation_manual_2025_2026.pdf": {
        "title": "Examinations, Evaluation & Malpractice Manual (2025–2026)",
        "dept_code": "COE",
        "doc_type": "EXAMINATION_MANUAL",
        "summary": "Hall ticket issuance, malpractice penalties, revaluation procedures, and arrear exams"
    },
    "04_hostel_and_residential_life_handbook_2025_2026.pdf": {
        "title": "Hostel & Residential Life Regulations & Safety Manual (2025–2026)",
        "dept_code": "HST",
        "doc_type": "HOSTEL_HANDBOOK",
        "summary": "Hostel room rents, mess timings, rebate rules, 8:30 PM curfew, and gate pass workflow"
    },
    "05_scholarships_and_financial_aid_circular_2025_2026.pdf": {
        "title": "Institutional & Governmental Scholarships and Financial Aid (2025–2026)",
        "dept_code": "SWO",
        "doc_type": "CIRCULAR",
        "summary": "First Graduate concession (₹25k), Merit waivers, sports awards, and SC/ST welfare"
    },
    "06_training_internship_and_placement_policy_2025_2026.pdf": {
        "title": "Career Development & Campus Placement Policy (2025–2026)",
        "dept_code": "CDC",
        "doc_type": "POLICY",
        "summary": "Placement eligibility (6.5 CGPA), Tiers 1-3, Dream Offers, and mandatory internships"
    },
    "07_code_of_conduct_ethics_and_anti_ragging_policy_2025_2026.pdf": {
        "title": "Code of Conduct, Campus Ethics & Statutory Anti-Ragging Policy (2025–2026)",
        "dept_code": "DSC",
        "doc_type": "STATUTORY_POLICY",
        "summary": "Statutory anti-ragging penalties, 24h police FIR mandate, squad contacts, and helplines"
    },
    "08_internal_complaints_committee_posh_charter_2025_2026.pdf": {
        "title": "Internal Complaints Committee (ICC) & PoSH Policy Charter (2025–2026)",
        "dept_code": "ICC",
        "doc_type": "STATUTORY_POLICY",
        "summary": "PoSH Act 2013 compliance, ICC roster, 90-day inquiry procedure, and confidentiality"
    },
    "09_central_library_and_digital_resources_policy_2025_2026.pdf": {
        "title": "Central Library Regulations, Digital Access & Plagiarism Policy (2025–2026)",
        "dept_code": "LIB",
        "doc_type": "POLICY",
        "summary": "Book borrowing quotas, overdue fines, digital databases, and Turnitin similarity limit (≤15%)"
    },
    "10_student_grievance_redressal_and_ombudsperson_manual_2025_2026.pdf": {
        "title": "Student Grievance Redressal & University Ombudsperson Manual (2025–2026)",
        "dept_code": "SGR",
        "doc_type": "MANUAL",
        "summary": "4-Tier escalation hierarchy, 15-day resolution SLA, and anti-victimisation guarantee"
    },
    "11_campus_health_transport_and_student_amenities_2025_2026.pdf": {
        "title": "Campus Health Services, Fleet Transport & Student Amenities (2025–2026)",
        "dept_code": "HLT",
        "doc_type": "AMENITIES_GUIDE",
        "summary": "24/7 ICU Ambulance, ₹1L cashless medical insurance, 45 bus routes, and cafeteria"
    },
    "12_student_clubs_sports_and_extracurricular_handbook_2025_2026.pdf": {
        "title": "Student Clubs, Professional Chapters, Sports & Cultural Handbook (2025–2026)",
        "dept_code": "ACT",
        "doc_type": "HANDBOOK",
        "summary": "Technical chapters (IEEE, ACM, SAE), NSS, NCC, 15 days On-Duty policy, and fests"
    },
}


async def setup_master_records(db: AsyncSession):
    """Ensures Academic Year 2025-2026, all Departments, and Admin User exist."""
    print("=== [1/4] Ensuring Academic Year, Departments & Admin Master Records ===")
    
    # 1. Academic Year
    ay_res = await db.execute(select(AcademicYears).where(AcademicYears.code == "2025-2026"))
    ay = ay_res.scalars().first()
    if not ay:
        ay = AcademicYears(
            code="2025-2026",
            start_date=datetime.date(2025, 6, 1),
            end_date=datetime.date(2026, 5, 31),
            is_current=True
        )
        db.add(ay)
        await db.commit()
        await db.refresh(ay)
        print("  ✓ Created Academic Year: 2025–2026 (Active)")
    else:
        ay.is_current = True
        await db.commit()
        print("  ✓ Academic Year 2025–2026 is active.")

    # 2. Departments
    dept_map = {}
    for d in DEPARTMENTS_CONFIG:
        res = await db.execute(select(Departments).where(Departments.code == d["code"]))
        existing = res.scalars().first()
        if not existing:
            dept_obj = Departments(
                code=d["code"],
                name=d["name"],
                contact_email=d["contact_email"],
                is_active=True
            )
            db.add(dept_obj)
            await db.commit()
            await db.refresh(dept_obj)
            dept_map[d["code"]] = dept_obj
        else:
            dept_map[d["code"]] = existing
    print(f"  ✓ Verified {len(dept_map)} Institutional Departments in Database.")

    # 3. Super Admin
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
        print("  ✓ Created Super Admin: admin@college.edu")

    return ay, dept_map, admin_user


async def ingest_single_document(
    db: AsyncSession,
    pdf_path: pathlib.Path,
    meta: dict,
    ay: AcademicYears,
    dept_map: dict,
    admin_user: Users,
    embedder
):
    """Extracts, chunks, embeds, and saves a single PDF document."""
    file_bytes = pdf_path.read_bytes()
    checksum = calculate_sha256(file_bytes)
    file_size = len(file_bytes)
    file_name = pdf_path.name
    dept = dept_map.get(meta["dept_code"], dept_map["GEN"])

    # 1. Clean up old records with same filename if re-ingesting
    old_doc_res = await db.execute(select(Documents).where(Documents.file_name == file_name))
    old_doc = old_doc_res.scalars().first()
    if old_doc:
        await db.delete(old_doc)
        await db.commit()

    # 2. Extract pages and create semantic chunks
    extracted_pages = pdf_service.extract_pages(file_bytes)
    chunks_data = pdf_service.chunk_document(
        pages=extracted_pages,
        document_title=meta["title"],
        academic_year="2025-2026",
        department=dept.name,
        max_chunk_chars=650,
        overlap_chars=80,
    )

    # 3. Compute vector embeddings
    chunk_texts = [c.content for c in chunks_data]
    embeddings = await embedder.get_embeddings_batch(chunk_texts)

    # 4. Safe storage target
    doc_id = uuid.uuid4()
    storage_target = pdf_service.generate_safe_storage_path(
        document_id=doc_id,
        version_number=1,
        original_filename=file_name
    )
    storage_target.write_bytes(file_bytes)

    # 5. Insert Document Record
    new_doc = Documents(
        id=doc_id,
        title=meta["title"],
        file_name=file_name,
        storage_path=str(storage_target),
        mime_type="application/pdf",
        file_size_bytes=file_size,
        checksum_sha256=checksum,
        version_number=1,
        status=DocumentStatus.PUBLISHED,
        document_type=meta["doc_type"],
        language_code="en",
        academic_year_id=ay.id,
        department_id=dept.id,
        uploaded_by_id=admin_user.id,
        approved_by_id=admin_user.id,
    )
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)

    # 6. Insert Version Record
    version_id = uuid.uuid4()
    new_version = DocumentVersions(
        id=version_id,
        document_id=new_doc.id,
        version_number=1,
        file_name=file_name,
        storage_path=str(storage_target),
        mime_type="application/pdf",
        file_size_bytes=file_size,
        checksum_sha256=checksum,
        status=DocumentStatus.PUBLISHED,
        document_type=meta["doc_type"],
        language_code="en",
        change_summary=meta["summary"],
        page_count=len(extracted_pages),
        chunk_count=len(chunks_data),
        created_by_id=admin_user.id,
        approved_by_id=admin_user.id,
    )
    db.add(new_version)
    await db.commit()
    await db.refresh(new_version)

    new_doc.active_version_id = new_version.id
    await db.commit()

    # 7. Insert Chunks with pgvector embeddings
    for c_info, emb_vec in zip(chunks_data, embeddings):
        chunk_rec = DocumentChunks(
            document_id=new_doc.id,
            version_id=new_version.id,
            chunk_index=c_info.chunk_index,
            page_number=c_info.page_number,
            content=c_info.content,
            token_count=c_info.token_count,
            embedding=emb_vec,
            chunk_metadata=c_info.metadata,
        )
        db.add(chunk_rec)

    await db.commit()

    return new_doc, len(extracted_pages), len(chunks_data)


async def ingest_all_documents():
    """Ingests all documents from the college_documents_pdf directory."""
    print("=" * 85)
    print("STARTING COMPLETE COLLEGE DOCUMENTS INGESTION INTO PGVECTOR")
    print("=" * 85)

    if not PDF_DIR.exists():
        raise FileNotFoundError(f"PDF directory not found at {PDF_DIR}")

    engine = create_async_engine(BaseConfig.DB_URI, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    embedder = get_embedding_provider()

    total_docs = 0
    total_pages = 0
    total_chunks = 0

    async with async_session() as db:
        ay, dept_map, admin_user = await setup_master_records(db)

        print("\n=== [2/4] Parsing, Chunking & Embedding All Institutional Documents ===")
        
        pdf_files = sorted(PDF_DIR.glob("*.pdf"))
        if not pdf_files:
            raise FileNotFoundError(f"No PDF files found in {PDF_DIR}")

        for pdf_file in pdf_files:
            meta = DOCUMENT_METADATA.get(pdf_file.name, {
                "title": pdf_file.stem.replace("_", " ").title(),
                "dept_code": "GEN",
                "doc_type": "REGULATION",
                "summary": "Official college document"
            })

            doc_obj, p_count, c_count = await ingest_single_document(
                db=db,
                pdf_path=pdf_file,
                meta=meta,
                ay=ay,
                dept_map=dept_map,
                admin_user=admin_user,
                embedder=embedder,
            )
            total_docs += 1
            total_pages += p_count
            total_chunks += c_count

            print(f"  ✓ Ingested: {pdf_file.name:<62} | {p_count} Pages | {c_count} Chunks Indexed")

        # Database index stats
        chunk_count_res = await db.execute(text("SELECT count(*) FROM document_chunks;"))
        db_total_chunks = chunk_count_res.scalar()

        doc_count_res = await db.execute(text("SELECT count(*) FROM documents WHERE status IN ('ACTIVE', 'PUBLISHED');"))
        db_total_docs = doc_count_res.scalar()

        print("-" * 85)
        print(f"INGESTION COMPLETED: {total_docs} Documents | {total_pages} Pages | {total_chunks} Chunks Added")
        print(f"DATABASE TOTAL: {db_total_docs} Published Documents | {db_total_chunks} Total Vector Chunks Active")
        print("-" * 85)

        # ── VERIFICATION SUITE ────────────────────────────────────────────────
        print("\n=== [3/4] Running Comprehensive Verification Queries across Document Domains ===")
        rag = RAGOrchestrationService()

        test_queries = [
            ("Admissions", "What is the annual tuition fee for B.E. Computer Science and when is the payment deadline?"),
            ("Hostel", "What is the refundable caution deposit fee for hostel admission and what is the curfew time?"),
            ("Examinations", "What is the minimum attendance required for semester exams and what is the condonation fee?"),
            ("Revaluation", "How much is the exam revaluation fee per subject and within how many days must a student apply?"),
            ("Scholarships", "What is the annual concession amount for First Generation Graduate students?"),
            ("Placements", "What is the minimum CGPA required to register for campus placements and what are the dream offer salary tiers?"),
            ("Anti-Ragging", "What is the national toll-free helpline number for anti-ragging complaints and what is the FIR mandate?"),
            ("Library", "How many books can an undergraduate student borrow and what is the maximum Turnitin plagiarism threshold?"),
            ("Grievance", "What is the 4-tier escalation hierarchy and resolution timeline for student grievances?"),
            ("Health & Bus", "What is the annual bus fee for Zone 2 and what is the 24x7 emergency medical helpline extension?"),
            ("Sports & Clubs", "How many days of academic On-Duty (OD) attendance are granted for sports representation?"),
            ("Ungrounded Query", "Who won the ICC Cricket World Cup in 1983?")
        ]

        passed_checks = 0
        for domain, q in test_queries:
            resp = await rag.answer_query(
                db=db,
                query=q,
                session_id=uuid.uuid4(),
                language="en",
                academic_year="2025-2026",
            )
            top_sim = resp.confidence_score
            doc_cited = resp.citations[0].document_title if resp.citations else "None (Safe Fallback)"
            page_cited = resp.citations[0].page_number if resp.citations else "-"

            threshold = BaseConfig.RAG_CONFIDENCE_THRESHOLD
            status = "PASS"
            if domain == "Ungrounded Query":
                if resp.fallback_triggered and top_sim < threshold:
                    status = "PASS (Safe Refusal)"
                else:
                    status = "FAIL"
            else:
                if not resp.fallback_triggered and top_sim >= threshold and len(resp.citations) > 0:
                    status = "PASS (Grounded)"
                else:
                    status = "FAIL"

            if "PASS" in status:
                passed_checks += 1

            print(f"\n[{status}] Domain: {domain}")
            print(f"  Q: \"{q}\"")
            print(f"  Similarity: {top_sim:.3f} | Fallback: {resp.fallback_triggered} | Cited: {doc_cited} (Page {page_cited})")
            print(f"  Answer: {resp.response[:140]}...")

        print("\n" + "=" * 85)
        print(f"VERIFICATION SCORE: {passed_checks}/{len(test_queries)} Checks Passed Successfully!")
        print("All documents are indexed in PostgreSQL pgvector and ready for public/admin chatbot use!")
        print("=" * 85)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(ingest_all_documents())
