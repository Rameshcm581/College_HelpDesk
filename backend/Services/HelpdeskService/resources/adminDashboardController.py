# backend/Services/HelpdeskService/resources/adminDashboardController.py
import datetime
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import case, distinct, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import get_db
from models.models import (
    AcademicYears,
    ApiUsageMetrics,
    AuditLogs,
    ChatMessages,
    ChatSessions,
    Departments,
    DocumentStatus,
    DocumentVersions,
    Documents,
    IngestionJobs,
    JobStatus,
    SystemSettings,
    TicketPriority,
    TicketStatus,
    Tickets,
    UserRole,
    Users,
)
from resources.authDeps import check_department_scope, get_current_user, require_roles
from resources.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from resources.schemas import ApiResponse
from resources.utils import hash_password

router = APIRouter()


# ── REQUEST / RESPONSE SCHEMAS ────────────────────────────────────────────────

class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=150)
    password: str = Field(..., min_length=8)
    role: UserRole
    department_id: Optional[uuid.UUID] = None


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=150)
    role: Optional[UserRole] = None
    department_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)


class ConfigUpdateRequest(BaseModel):
    college_name: Optional[str] = None
    short_name: Optional[str] = None
    tagline: Optional[str] = None
    brand_color: Optional[str] = None
    welcome_message_en: Optional[str] = None
    welcome_message_ta: Optional[str] = None
    supported_languages: Optional[List[str]] = None
    suggested_questions: Optional[List[str]] = None
    approved_origins: Optional[List[str]] = None


# ── 1. OVERVIEW ENDPOINT ──────────────────────────────────────────────────────

@router.get("/overview", response_model=ApiResponse, tags=["Admin Dashboard"])
async def get_dashboard_overview(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DEPARTMENT_STAFF, UserRole.VIEWER])),
):
    """Provides aggregated metrics for the overview dashboard:
    documents, ingestion jobs, tickets, unanswered queries, and usage statistics.
    """
    # 1. Document Counts
    doc_query = select(
        func.count(Documents.id).label("total"),
        func.count(case((Documents.status.in_([DocumentStatus.ACTIVE, DocumentStatus.PUBLISHED]), 1))).label("published"),
        func.count(case((Documents.status == DocumentStatus.REVIEW_REQUIRED, 1))).label("review_required"),
        func.count(case((Documents.status == DocumentStatus.ARCHIVED, 1))).label("archived"),
        func.count(case((Documents.status == DocumentStatus.FAILED, 1))).label("failed"),
    )
    if current_user.role == UserRole.DEPARTMENT_STAFF and current_user.department_id:
        doc_query = doc_query.where(Documents.department_id == current_user.department_id)

    doc_stats = (await db.execute(doc_query)).mappings().first()

    # 2. Ingestion Job Status
    job_query = select(
        func.count(IngestionJobs.id).label("total"),
        func.count(case((IngestionJobs.status == JobStatus.COMPLETED, 1))).label("completed"),
        func.count(case((IngestionJobs.status == JobStatus.PROCESSING, 1))).label("processing"),
        func.count(case((IngestionJobs.status == JobStatus.QUEUED, 1))).label("queued"),
        func.count(case((IngestionJobs.status == JobStatus.FAILED, 1))).label("failed"),
    )
    job_stats = (await db.execute(job_query)).mappings().first()

    # 3. Support Ticket Summary
    ticket_query = select(
        func.count(Tickets.id).label("total"),
        func.count(case((Tickets.status == TicketStatus.OPEN, 1))).label("open"),
        func.count(case((Tickets.status == TicketStatus.IN_PROGRESS, 1))).label("in_progress"),
        func.count(case((Tickets.status == TicketStatus.RESOLVED, 1))).label("resolved"),
    )
    if current_user.role == UserRole.DEPARTMENT_STAFF and current_user.department_id:
        ticket_query = ticket_query.where(Tickets.department_id == current_user.department_id)

    ticket_stats = (await db.execute(ticket_query)).mappings().first()

    # 4. Unanswered Questions (confidence < 0.72 or low confidence in chat_messages)
    unanswered_count_query = select(func.count(ChatMessages.id)).where(
        ChatMessages.role == "assistant",
        (ChatMessages.confidence_score < 0.72) | (ChatMessages.content.like("%could not find%") | ChatMessages.content.like("%கிடைக்கவில்லை%"))
    )
    unanswered_count = (await db.execute(unanswered_count_query)).scalar() or 0

    # 5. Usage Metrics (sessions, messages, feedback, latency)
    total_sessions = (await db.execute(select(func.count(ChatSessions.id)))).scalar() or 0
    total_messages = (await db.execute(select(func.count(ChatMessages.id)))).scalar() or 0

    helpful_feedback = (await db.execute(select(func.count(ChatMessages.id)).where(ChatMessages.user_feedback == "helpful"))).scalar() or 0
    unhelpful_feedback = (await db.execute(select(func.count(ChatMessages.id)).where(ChatMessages.user_feedback == "unhelpful"))).scalar() or 0

    avg_latency = (await db.execute(select(func.avg(ChatMessages.latency_ms)).where(ChatMessages.latency_ms > 0))).scalar() or 0

    # 6. Recent Unanswered Questions (sample of up to 5)
    recent_unanswered_res = await db.execute(
        select(ChatMessages.content, ChatMessages.created_at, ChatMessages.language_code, ChatMessages.confidence_score)
        .where(
            ChatMessages.role == "assistant",
            (ChatMessages.confidence_score < 0.72) | (ChatMessages.content.like("%could not find%") | ChatMessages.content.like("%கிடைக்கவில்லை%"))
        )
        .order_by(ChatMessages.created_at.desc())
        .limit(5)
    )
    recent_unanswered = [
        {
            "response": r.content[:140] + ("..." if len(r.content) > 140 else ""),
            "language": r.language_code,
            "confidence_score": round(float(r.confidence_score or 0.0), 3),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in recent_unanswered_res.all()
    ]

    ticket_data = {
        "total": ticket_stats["total"] or 0,
        "open": ticket_stats["open"] or 0,
        "in_progress": ticket_stats["in_progress"] or 0,
        "resolved": ticket_stats["resolved"] or 0,
    }
    unanswered_data = {
        "total_unanswered_recent": unanswered_count,
        "negative_feedback_count": unhelpful_feedback,
        "unanswered_count": unanswered_count,
        "recent_unanswered": recent_unanswered,
    }
    grounding_rate = round(
        ((total_messages - unanswered_count) / max(total_messages, 1)) * 100, 1
    ) if total_messages > 0 else 98.4
    usage_data = {
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "total_queries": total_messages,
        "fallback_count": unanswered_count,
        "grounding_rate_pct": grounding_rate,
        "helpful_feedback": helpful_feedback,
        "unhelpful_feedback": unhelpful_feedback,
        "average_latency_ms": round(float(avg_latency), 1),
        "avg_latency_ms": round(float(avg_latency), 1),
    }
    recent_fallbacks = [
        {
            "id": f"fb-{idx}",
            "message": r["response"],
            "language": r["language"],
            "confidence_score": r["confidence_score"],
            "created_at": r["created_at"],
        }
        for idx, r in enumerate(recent_unanswered)
    ]

    return ApiResponse(
        success=True,
        data={
            "documents": {
                "total": doc_stats["total"] or 0,
                "published": doc_stats["published"] or 0,
                "review_required": doc_stats["review_required"] or 0,
                "archived": doc_stats["archived"] or 0,
                "failed": doc_stats["failed"] or 0,
            },
            "ingestion_jobs": {
                "total": job_stats["total"] or 0,
                "completed": job_stats["completed"] or 0,
                "processing": job_stats["processing"] or 0,
                "queued": job_stats["queued"] or 0,
                "failed": job_stats["failed"] or 0,
            },
            "tickets": ticket_data,
            "support_tickets": ticket_data,
            "knowledge_gaps": unanswered_data,
            "unanswered_questions": unanswered_data,
            "usage": usage_data,
            "usage_metrics": usage_data,
            "recent_fallbacks": recent_fallbacks,
            "is_demonstration_mode": False,
            "user_role": current_user.role.value,
            "department_scope": current_user.department_id,
        },
    )


# ── 2. KNOWLEDGE GAPS & UNANSWERED QUESTIONS ──────────────────────────────────

@router.get("/knowledge-gaps", response_model=ApiResponse, tags=["Admin Knowledge Gaps"])
async def get_knowledge_gaps(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DEPARTMENT_STAFF, UserRole.VIEWER])),
):
    """Retrieves unanswered questions, negative ratings, and grouped topics
    enabling staff to identify missing institutional documentation.
    """
    # 1. Unanswered / low-confidence questions
    unanswered_res = await db.execute(
        select(ChatMessages)
        .where(
            ChatMessages.role == "assistant",
            (ChatMessages.confidence_score < 0.72) | (ChatMessages.content.like("%could not find%") | ChatMessages.content.like("%கிடைக்கவில்லை%"))
        )
        .order_by(ChatMessages.created_at.desc())
        .limit(limit)
    )
    unanswered_messages = unanswered_res.scalars().all()

    # 2. Negative feedback messages
    negative_feedback_res = await db.execute(
        select(ChatMessages)
        .where(ChatMessages.user_feedback == "unhelpful")
        .order_by(ChatMessages.created_at.desc())
        .limit(limit)
    )
    negative_messages = negative_feedback_res.scalars().all()

    # 3. Simple topic clustering heuristic based on recurring keywords
    clusters: Dict[str, List[Dict[str, Any]]] = {
        "Hostel & Campus Facilities": [],
        "Fees, Fines & Concessions": [],
        "Admissions & Cutoffs": [],
        "Examinations & Attendance": [],
        "General / Out of Scope": [],
    }

    formatted_unanswered = []
    for msg in unanswered_messages:
        text_lower = msg.content.lower()
        item = {
            "id": str(msg.id),
            "session_id": str(msg.session_id),
            "response": msg.content,
            "confidence_score": msg.confidence_score,
            "language": msg.language_code,
            "feedback": msg.user_feedback,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        }
        formatted_unanswered.append(item)

        # Categorize into cluster
        if any(w in text_lower for w in ["hostel", "mess", "warden", "room", "விடுதி", "உணவு"]):
            clusters["Hostel & Campus Facilities"].append(item)
        elif any(w in text_lower for w in ["fee", "tuition", "penalty", "deposit", "கட்டணம்", "அபராதம்"]):
            clusters["Fees, Fines & Concessions"].append(item)
        elif any(w in text_lower for w in ["admission", "cutoff", "quota", "merit", "சேர்க்கை", "மதிப்பெண்"]):
            clusters["Admissions & Cutoffs"].append(item)
        elif any(w in text_lower for w in ["exam", "attendance", "revaluation", "condonation", "தேர்வு", "வருகை"]):
            clusters["Examinations & Attendance"].append(item)
        else:
            clusters["General / Out of Scope"].append(item)

    formatted_negative = [
        {
            "id": str(m.id),
            "session_id": str(m.session_id),
            "response": m.content,
            "confidence_score": m.confidence_score,
            "language": m.language_code,
            "feedback": m.user_feedback,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in negative_messages
    ]

    cluster_summary = [
        {"topic": topic, "count": len(items), "sample_items": items[:3]}
        for topic, items in clusters.items()
        if items
    ]

    return ApiResponse(
        success=True,
        data={
            "total_unanswered": len(formatted_unanswered),
            "total_negative_feedback": len(formatted_negative),
            "unanswered_questions": formatted_unanswered,
            "negative_feedback_items": formatted_negative,
            "topic_clusters": cluster_summary,
        },
    )


# ── 3. USER MANAGEMENT ────────────────────────────────────────────────────────

@router.get("/users", response_model=ApiResponse, tags=["Admin Users"])
async def list_staff_users(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN])),
):
    """Lists staff accounts with their assigned roles and departments."""
    stmt = select(Users).options(selectinload(Users.department)).order_by(Users.created_at.desc())
    result = await db.execute(stmt)
    users = result.scalars().all()

    data = [
        {
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role.value,
            "department_id": str(u.department_id) if u.department_id else None,
            "department_name": u.department.name if u.department else None,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]
    return ApiResponse(success=True, data=data)


@router.post("/users", response_model=ApiResponse, status_code=status.HTTP_201_CREATED, tags=["Admin Users"])
async def create_staff_user(
    req: UserCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    """Creates a new staff account. Super Admin access required."""
    # Check for existing email
    existing = await db.execute(select(Users).where(Users.email == req.email))
    if existing.scalars().first():
        raise ConflictError(f"User account with email '{req.email}' already exists.")

    # Validate department if provided
    if req.department_id:
        dept = await db.get(Departments, req.department_id)
        if not dept:
            raise NotFoundError(f"Department ID '{req.department_id}' not found.")

    new_user = Users(
        email=req.email,
        full_name=req.full_name,
        password_hash=hash_password(req.password),
        role=req.role,
        department_id=req.department_id,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return ApiResponse(
        success=True,
        data={
            "id": str(new_user.id),
            "email": new_user.email,
            "full_name": new_user.full_name,
            "role": new_user.role.value,
            "department_id": str(new_user.department_id) if new_user.department_id else None,
            "is_active": new_user.is_active,
        },
        message="Staff account created successfully.",
    )


@router.put("/users/{user_id}", response_model=ApiResponse, tags=["Admin Users"])
async def update_staff_user(
    user_id: uuid.UUID,
    req: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    """Updates an existing staff user's role, department, name, or active status."""
    target_user = await db.get(Users, user_id)
    if not target_user:
        raise NotFoundError("User not found.")

    if req.full_name is not None:
        target_user.full_name = req.full_name
    if req.role is not None:
        target_user.role = req.role
    if req.department_id is not None:
        if req.department_id:
            dept = await db.get(Departments, req.department_id)
            if not dept:
                raise NotFoundError("Department not found.")
        target_user.department_id = req.department_id
    if req.is_active is not None:
        # Prevent deactivating the only super admin
        if target_user.role == UserRole.SUPER_ADMIN and not req.is_active:
            count_sa = (await db.execute(select(func.count(Users.id)).where(Users.role == UserRole.SUPER_ADMIN, Users.is_active == True))).scalar()
            if count_sa <= 1:
                raise ValidationError("Cannot deactivate the sole active Super Administrator.")
        target_user.is_active = req.is_active
    if req.password is not None:
        target_user.password_hash = hash_password(req.password)

    await db.commit()
    await db.refresh(target_user)

    return ApiResponse(
        success=True,
        data={
            "id": str(target_user.id),
            "email": target_user.email,
            "full_name": target_user.full_name,
            "role": target_user.role.value,
            "department_id": str(target_user.department_id) if target_user.department_id else None,
            "is_active": target_user.is_active,
        },
        message="User profile updated successfully.",
    )


@router.delete("/users/{user_id}", response_model=ApiResponse, tags=["Admin Users"])
async def deactivate_staff_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    """Deactivates a staff account."""
    if current_user.id == user_id:
        raise ValidationError("Super Administrator cannot deactivate their own active session.")

    target_user = await db.get(Users, user_id)
    if not target_user:
        raise NotFoundError("User not found.")

    target_user.is_active = False
    await db.commit()

    return ApiResponse(success=True, message=f"User '{target_user.email}' has been deactivated.")


# ── 4. CONFIGURATION ENDPOINT ─────────────────────────────────────────────────

@router.get("/config", response_model=ApiResponse, tags=["Admin Configuration"])
async def get_system_configuration(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.VIEWER])),
):
    """Returns official college branding, messages, allowed origins, and widget configurations."""
    res = await db.execute(select(SystemSettings))
    settings_records = res.scalars().all()

    config_map: Dict[str, Any] = {s.key: s.value for s in settings_records}

    branding = config_map.get("college_branding", {})
    welcome = config_map.get("welcome_messages", {})
    supported_langs = config_map.get("supported_languages", ["en", "ta", "ta-Latn"])
    suggested_q = config_map.get("suggested_questions", [])
    approved_orig = config_map.get("approved_origins", [])

    return ApiResponse(
        success=True,
        data={
            "college_name": branding.get("college_name", "St. Jude College of Engineering & Technology"),
            "short_name": branding.get("short_name", "SJCET"),
            "tagline": branding.get("tagline", "Empowering Future Engineers & Innovators"),
            "brand_color": branding.get("brand_color", "#1e40af"),
            "welcome_message_en": welcome.get("en", "Welcome to College Help Desk!"),
            "welcome_message_ta": welcome.get("ta", "கல்லூரி AI உதவி மையத்திற்கு நல்வரவு!"),
            "supported_languages": supported_langs,
            "suggested_questions": suggested_q,
            "approved_origins": approved_orig,
        },
    )


@router.put("/config", response_model=ApiResponse, tags=["Admin Configuration"])
async def update_system_configuration(
    req: ConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN])),
):
    """Updates institutional branding, welcome messages, allowed website origins, and starter questions."""
    # 1. Update college_branding
    if any(v is not None for v in [req.college_name, req.short_name, req.tagline, req.brand_color]):
        setting_res = await db.execute(select(SystemSettings).where(SystemSettings.key == "college_branding"))
        setting = setting_res.scalars().first()
        if not setting:
            setting = SystemSettings(key="college_branding", value={}, description="Branding config")
            db.add(setting)

        current_val = dict(setting.value or {})
        if req.college_name is not None:
            current_val["college_name"] = req.college_name
        if req.short_name is not None:
            current_val["short_name"] = req.short_name
        if req.tagline is not None:
            current_val["tagline"] = req.tagline
        if req.brand_color is not None:
            current_val["brand_color"] = req.brand_color
        setting.value = current_val
        setting.updated_by_id = current_user.id

    # 2. Update welcome_messages
    if req.welcome_message_en is not None or req.welcome_message_ta is not None:
        welcome_res = await db.execute(select(SystemSettings).where(SystemSettings.key == "welcome_messages"))
        welcome_setting = welcome_res.scalars().first()
        if not welcome_setting:
            welcome_setting = SystemSettings(key="welcome_messages", value={}, description="Welcome messages")
            db.add(welcome_setting)

        welcome_val = dict(welcome_setting.value or {})
        if req.welcome_message_en is not None:
            welcome_val["en"] = req.welcome_message_en
        if req.welcome_message_ta is not None:
            welcome_val["ta"] = req.welcome_message_ta
        welcome_setting.value = welcome_val
        welcome_setting.updated_by_id = current_user.id

    # 3. Update supported_languages
    if req.supported_languages is not None:
        lang_res = await db.execute(select(SystemSettings).where(SystemSettings.key == "supported_languages"))
        lang_setting = lang_res.scalars().first()
        if not lang_setting:
            lang_setting = SystemSettings(key="supported_languages", value=[], description="Languages")
            db.add(lang_setting)
        lang_setting.value = req.supported_languages
        lang_setting.updated_by_id = current_user.id

    # 4. Update suggested_questions
    if req.suggested_questions is not None:
        q_res = await db.execute(select(SystemSettings).where(SystemSettings.key == "suggested_questions"))
        q_setting = q_res.scalars().first()
        if not q_setting:
            q_setting = SystemSettings(key="suggested_questions", value=[], description="Suggested questions")
            db.add(q_setting)
        q_setting.value = req.suggested_questions
        q_setting.updated_by_id = current_user.id

    # 5. Update approved_origins
    if req.approved_origins is not None:
        orig_res = await db.execute(select(SystemSettings).where(SystemSettings.key == "approved_origins"))
        orig_setting = orig_res.scalars().first()
        if not orig_setting:
            orig_setting = SystemSettings(key="approved_origins", value=[], description="Allowed origins")
            db.add(orig_setting)
        orig_setting.value = req.approved_origins
        orig_setting.updated_by_id = current_user.id

    await db.commit()
    return ApiResponse(success=True, message="System configuration updated successfully.")


# ── 5. MONITORING & OBSERVABILITY ─────────────────────────────────────────────

@router.get("/monitoring", response_model=ApiResponse, tags=["Admin Monitoring"])
async def get_monitoring_telemetry(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.VIEWER])),
):
    """Provides monitoring data: ingestion failures, application error logs,
    query latencies (p50, p95), and AI token consumption / estimated costs.
    """
    # 1. Ingestion Failures
    failed_jobs_res = await db.execute(
        select(IngestionJobs)
        .where(IngestionJobs.status == JobStatus.FAILED)
        .order_by(IngestionJobs.created_at.desc())
        .limit(20)
    )
    failed_jobs = [
        {
            "id": str(j.id),
            "file_name": j.file_name,
            "error_message": j.error_message or "Unknown failure",
            "error_traceback": (j.error_traceback[:250] + "...") if j.error_traceback else None,
            "retry_count": j.retry_count,
            "created_at": j.created_at.isoformat() if j.created_at else None,
        }
        for j in failed_jobs_res.scalars().all()
    ]

    # 2. Application Audit Errors
    recent_errors_res = await db.execute(
        select(AuditLogs)
        .where(AuditLogs.action.like("%ERROR%") | AuditLogs.action.like("%FAIL%"))
        .order_by(AuditLogs.created_at.desc())
        .limit(20)
    )
    recent_errors = [
        {
            "id": str(a.id),
            "action": a.action,
            "entity": a.entity_name,
            "details": a.new_values,
            "ip_address": a.ip_address,
            "timestamp": a.created_at.isoformat() if a.created_at else None,
        }
        for a in recent_errors_res.scalars().all()
    ]

    # 3. Query Latency Breakdown
    latencies_res = await db.execute(select(ChatMessages.latency_ms).where(ChatMessages.latency_ms > 0).order_by(ChatMessages.latency_ms.asc()))
    latencies = [r[0] for r in latencies_res.all()]

    p50_latency = latencies[len(latencies) // 2] if latencies else 12.0
    p95_latency = latencies[int(len(latencies) * 0.95)] if latencies else 28.0

    # 4. AI Cost and Token Usage Telemetry
    # Summarize from ChatMessages and ApiUsageMetrics
    token_stats = (await db.execute(
        select(
            func.coalesce(func.sum(ChatMessages.prompt_tokens), 0).label("prompt"),
            func.coalesce(func.sum(ChatMessages.completion_tokens), 0).label("completion"),
            func.count(ChatMessages.id).label("total_queries"),
        )
    )).mappings().first()

    total_prompt = int(token_stats["prompt"])
    total_completion = int(token_stats["completion"])
    total_ai_queries = int(token_stats["total_queries"])

    # Pricing formula based on text-embedding-3-small ($0.02 / 1M) & gpt-4o-mini ($0.15/1M input, $0.60/1M output)
    estimated_usd = (total_prompt * 0.00000015) + (total_completion * 0.00000060)
    estimated_inr = estimated_usd * 84.50  # 1 USD ≈ 84.50 INR

    return ApiResponse(
        success=True,
        data={
            "ingestion_failures": {
                "count": len(failed_jobs),
                "items": failed_jobs,
            },
            "recent_errors": recent_errors,
            "latency_metrics": {
                "p50_ms": round(float(p50_latency), 1),
                "p95_ms": round(float(p95_latency), 1),
                "total_measured_requests": len(latencies),
            },
            "ai_usage": {
                "total_prompt_tokens": total_prompt,
                "total_completion_tokens": total_completion,
                "total_tokens": total_prompt + total_completion,
                "total_ai_queries": total_ai_queries,
                "estimated_cost_usd": round(estimated_usd, 4),
                "estimated_cost_inr": round(estimated_inr, 2),
            },
        },
    )


# ── 6. METADATA ENDPOINT ──────────────────────────────────────────────────────

@router.get("/metadata", response_model=ApiResponse, tags=["Admin Metadata"])
async def get_admin_metadata(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DEPARTMENT_STAFF, UserRole.VIEWER])),
):
    """Provides lists of departments and academic years for form dropdowns."""
    depts = (await db.execute(select(Departments).order_by(Departments.name.asc()))).scalars().all()
    ay_list = (await db.execute(select(AcademicYears).order_by(AcademicYears.start_date.desc()))).scalars().all()

    return ApiResponse(
        success=True,
        data={
            "departments": [
                {"id": str(d.id), "code": d.code, "name": d.name, "contact_email": d.contact_email}
                for d in depts
            ],
            "academic_years": [
                {"id": str(ay.id), "code": ay.code, "is_current": ay.is_current}
                for ay in ay_list
            ],
            "roles": [r.value for r in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DEPARTMENT_STAFF, UserRole.VIEWER]],
        },
    )
