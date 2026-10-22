# backend/Services/HelpdeskService/resources/ticketController.py
from datetime import datetime, timedelta, timezone
import hashlib
import logging
import os
import random
import secrets
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import get_db
from models.models import (
    ChatMessages,
    ChatSessions,
    Departments,
    TicketCategory,
    TicketMessages,
    TicketOtps,
    TicketPriority,
    TicketStatus,
    TicketStatusHistory,
    Tickets,
    UserRole,
    Users,
)
from resources.authDeps import check_department_scope, get_current_user, require_roles
from resources.emailService import email_service
from resources.errors import (
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    UnauthorizedError,
    ValidationError,
)
from resources.schemas import (
    ApiResponse,
    TicketAssignRequest,
    TicketCreateRequest,
    TicketMessageCreateRequest,
    TicketOtpRequest,
    TicketOtpVerifyRequest,
    TicketStatusUpdateRequest,
)
from resources.utils import create_access_token, decode_access_token

logger = logging.getLogger("helpdesk.ticketController")

public_router = APIRouter()
admin_router = APIRouter()

# ── ROUTING & SLA RULES ────────────────────────────────────────────────────────

CATEGORY_DEPARTMENT_MAP = {
    TicketCategory.ADMISSIONS.value: "ADM",
    TicketCategory.FEES.value: "FIN",
    TicketCategory.EXAMINATIONS.value: "EXM",
    TicketCategory.HOSTEL.value: "HST",
    TicketCategory.SCHOLARSHIPS.value: "SCH",
    TicketCategory.PLACEMENTS.value: "PLC",
    TicketCategory.GENERAL.value: "GEN",
}

SLA_HOURS_BY_PRIORITY = {
    TicketPriority.URGENT: 4,
    TicketPriority.HIGH: 12,
    TicketPriority.MEDIUM: 24,
    TicketPriority.LOW: 48,
}

VALID_STATUS_TRANSITIONS = {
    TicketStatus.OPEN: {TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS, TicketStatus.CLOSED},
    TicketStatus.ASSIGNED: {TicketStatus.IN_PROGRESS, TicketStatus.WAITING_FOR_USER, TicketStatus.RESOLVED, TicketStatus.CLOSED},
    TicketStatus.IN_PROGRESS: {TicketStatus.WAITING_FOR_USER, TicketStatus.RESOLVED, TicketStatus.CLOSED},
    TicketStatus.WAITING_FOR_USER: {TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED, TicketStatus.CLOSED},
    TicketStatus.RESOLVED: {TicketStatus.CLOSED, TicketStatus.IN_PROGRESS},
    TicketStatus.CLOSED: {TicketStatus.IN_PROGRESS},
}


# ── HELPERS ────────────────────────────────────────────────────────────────────

def _hash_otp(otp: str, ticket_id: uuid.UUID) -> str:
    """Generates SHA-256 hash of OTP salted with ticket ID."""
    return hashlib.sha256(f"{otp.strip()}:{ticket_id}".encode("utf-8")).hexdigest()


async def _generate_unique_ticket_number(db: AsyncSession) -> str:
    """Generates an institutional ticket identifier (e.g. TCK-2026-48291)."""
    current_year = datetime.now(timezone.utc).year
    for _ in range(10):
        candidate = f"TCK-{current_year}-{random.randint(10000, 99999)}"
        exists = await db.scalar(select(func.count(Tickets.id)).where(Tickets.ticket_number == candidate))
        if not exists:
            return candidate
    return f"TCK-{current_year}-{int(datetime.now(timezone.utc).timestamp()) % 100000:05d}"


async def _resolve_department_for_category(db: AsyncSession, category: str) -> Optional[Departments]:
    dept_code = CATEGORY_DEPARTMENT_MAP.get(category.upper().strip(), "GEN")
    res = await db.execute(select(Departments).where(Departments.code == dept_code))
    dept = res.scalars().first()
    if not dept:
        # Fallback to first available active department
        res_default = await db.execute(select(Departments).where(Departments.is_active == True).limit(1))
        dept = res_default.scalars().first()
    return dept


async def _verify_visitor_ticket_auth(ticket: Tickets, authorization: Optional[str]) -> bool:
    """Verifies that the request has a valid Bearer token scoped to this ticket or staff role."""
    if not authorization or not authorization.startswith("Bearer "):
        return False

    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload:
        return False

    # 1. Visitor ticket-scoped token
    if payload.get("type") == "visitor_ticket_access":
        return payload.get("sub") == ticket.ticket_number

    # 2. Staff user token
    if "sub" in payload:
        return True

    return False


# ── 1. PUBLIC TICKET CREATION ──────────────────────────────────────────────────

@public_router.post("/tickets", response_model=ApiResponse, status_code=status.HTTP_201_CREATED, tags=["Public Tickets"])
async def create_ticket(
    req: TicketCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Creates a student support ticket when:
    - Chatbot cannot find reliable answer (fallback triggered)
    - Visitor requests human assistance
    - Visitor reports an issue
    - Support category requires staff intervention
    """
    category_str = req.category.upper().strip()
    try:
        category_enum = TicketCategory(category_str)
    except ValueError:
        category_enum = TicketCategory.GENERAL

    try:
        priority_enum = TicketPriority(req.priority.upper().strip())
    except ValueError:
        priority_enum = TicketPriority.MEDIUM

    # 1. Resolve department via routing rules
    dept = await _resolve_department_for_category(db, category_enum.value)

    # 2. Calculate SLA deadline
    sla_hours = SLA_HOURS_BY_PRIORITY.get(priority_enum, 24)
    now = datetime.now(timezone.utc)
    sla_due_at = now + timedelta(hours=sla_hours)

    ticket_num = await _generate_unique_ticket_number(db)
    subject_text = req.subject.strip() if req.subject else f"{category_enum.value} Inquiry - {req.student_name}"

    new_ticket = Tickets(
        id=uuid.uuid4(),
        ticket_number=ticket_num,
        session_id=req.session_id,
        department_id=dept.id if dept else None,
        student_name=req.student_name.strip(),
        student_email=req.student_email.lower().strip(),
        student_phone=req.student_phone.strip() if req.student_phone else None,
        category=category_enum.value,
        priority=priority_enum,
        status=TicketStatus.OPEN,
        subject=subject_text,
        description=req.message.strip(),
        sla_due_at=sla_due_at,
    )
    db.add(new_ticket)
    await db.flush()

    # 3. Add initial student message
    initial_msg = TicketMessages(
        ticket_id=new_ticket.id,
        sender_type="STUDENT",
        message=req.message.strip(),
        is_internal_note=False,
    )
    db.add(initial_msg)

    # 4. Record initial status history
    history = TicketStatusHistory(
        ticket_id=new_ticket.id,
        from_status="NONE",
        to_status=TicketStatus.OPEN.value,
        change_reason="Ticket created by visitor via portal / chatbot fallback",
    )
    db.add(history)

    await db.commit()
    await db.refresh(new_ticket)

    # 5. Email notification dispatch (graceful, non-blocking failure handling)
    notification_sent = await email_service.notify_ticket_created(
        ticket_number=new_ticket.ticket_number,
        student_name=new_ticket.student_name,
        student_email=new_ticket.student_email,
        category=new_ticket.category,
        subject=new_ticket.subject,
    )

    return ApiResponse(
        success=True,
        data={
            "id": str(new_ticket.id),
            "ticket_number": new_ticket.ticket_number,
            "status": new_ticket.status.value,
            "category": new_ticket.category,
            "priority": new_ticket.priority.value,
            "department": dept.name if dept else "General Administration",
            "department_code": dept.code if dept else "GEN",
            "sla_due_at": new_ticket.sla_due_at.isoformat(),
            "notification_sent": notification_sent,
            "created_at": new_ticket.created_at.isoformat(),
            "tracking_url": f"/tickets/{new_ticket.ticket_number}",
        },
        message=f"Support ticket {new_ticket.ticket_number} created successfully.",
    )


# ── 2. VISITOR SECURE OTP AUTHENTICATION & TRACKING ────────────────────────────

@public_router.post("/tickets/{ticket_number}/request-otp", response_model=ApiResponse, tags=["Public Tickets"])
async def request_ticket_otp(
    ticket_number: str,
    req: TicketOtpRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generates and dispatches a cryptographically secure 6-digit OTP for visitor tracking.
    Never logs OTPs or secrets. Enforces rate limiting and expiration.
    """
    res = await db.execute(select(Tickets).where(Tickets.ticket_number == ticket_number))
    ticket = res.scalars().first()
    if not ticket:
        raise NotFoundError(f"Ticket with identifier '{ticket_number}' not found.")

    # Strict email verification
    if ticket.student_email.lower().strip() != req.email.lower().strip():
        raise UnauthorizedError("Email does not match the registered ticket requester address.")

    # Rate limiting: max 3 requests per 10 minutes per ticket
    ten_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
    recent_count = await db.scalar(
        select(func.count(TicketOtps.id))
        .where(TicketOtps.ticket_id == ticket.id)
        .where(TicketOtps.created_at >= ten_mins_ago)
    )
    if recent_count and recent_count >= 3:
        raise RateLimitError("Too many OTP requests. Please wait 10 minutes before requesting a new code.")

    # Invalidate prior unused OTPs for this ticket
    prior_otps = await db.execute(
        select(TicketOtps)
        .where(TicketOtps.ticket_id == ticket.id)
        .where(TicketOtps.is_used == False)
    )
    for p in prior_otps.scalars().all():
        p.is_used = True

    # Generate 6-digit cryptographically secure OTP
    raw_otp = f"{secrets.randbelow(900000) + 100000:06d}"
    hashed = _hash_otp(raw_otp, ticket.id)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    otp_record = TicketOtps(
        ticket_id=ticket.id,
        email=ticket.student_email,
        otp_hash=hashed,
        expires_at=expires_at,
        attempts=0,
        max_attempts=3,
        is_used=False,
    )
    db.add(otp_record)
    await db.commit()

    # Dispatch email (NEVER log OTP!)
    logger.info("OTP generated for ticket %s (email: %s, expires: %s)", ticket.ticket_number, ticket.student_email, expires_at)
    delivery_success = await email_service.send_otp_email(
        to_email=ticket.student_email,
        ticket_number=ticket.ticket_number,
        otp_code=raw_otp,
        expires_minutes=15,
    )

    res_data = {
        "ticket_number": ticket.ticket_number,
        "email_masked": f"{ticket.student_email[:2]}***@{ticket.student_email.split('@')[-1]}",
        "expires_in_seconds": 900,
        "email_dispatched": delivery_success,
    }
    if not delivery_success and os.getenv("ENVIRONMENT", "development").lower() != "production":
        res_data["dev_otp_hint"] = raw_otp

    return ApiResponse(
        success=True,
        data=res_data,
        message="A 6-digit verification code has been dispatched to your email address.",
    )


@public_router.post("/tickets/{ticket_number}/verify-otp", response_model=ApiResponse, tags=["Public Tickets"])
async def verify_ticket_otp(
    ticket_number: str,
    req: TicketOtpVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verifies visitor OTP with attempt limits, expiration, and issues a scoped access token."""
    res = await db.execute(select(Tickets).where(Tickets.ticket_number == ticket_number))
    ticket = res.scalars().first()
    if not ticket:
        raise NotFoundError(f"Ticket '{ticket_number}' not found.")

    if ticket.student_email.lower().strip() != req.email.lower().strip():
        raise UnauthorizedError("Email does not match registered requester.")

    now = datetime.now(timezone.utc)
    res_otp = await db.execute(
        select(TicketOtps)
        .where(TicketOtps.ticket_id == ticket.id)
        .where(TicketOtps.is_used == False)
        .where(TicketOtps.expires_at > now)
        .order_by(TicketOtps.created_at.desc())
    )
    otp_record = res_otp.scalars().first()
    if not otp_record:
        raise ValidationError("OTP code has expired or was not requested. Please request a new code.")

    # Check attempt limits
    if otp_record.attempts >= otp_record.max_attempts:
        otp_record.is_used = True
        await db.commit()
        raise RateLimitError("Maximum verification attempts exceeded. Please request a new OTP.")

    # Verify hash
    expected_hash = _hash_otp(req.otp, ticket.id)
    if expected_hash != otp_record.otp_hash:
        otp_record.attempts += 1
        await db.commit()
        remaining = otp_record.max_attempts - otp_record.attempts
        raise UnauthorizedError(f"Invalid verification code. {remaining} attempt(s) remaining.")

    # Success: Mark OTP as used and generate scoped visitor token
    otp_record.is_used = True
    await db.commit()

    token_payload = {
        "sub": ticket.ticket_number,
        "ticket_id": str(ticket.id),
        "email": ticket.student_email,
        "type": "visitor_ticket_access",
    }
    visitor_token = create_access_token(token_payload, expires_delta=timedelta(hours=4))

    return ApiResponse(
        success=True,
        data={
            "ticket_number": ticket.ticket_number,
            "access_token": visitor_token,
            "expires_in": 14400,
        },
        message="OTP verified successfully. Ticket tracking session granted.",
    )


@public_router.get("/tickets/{ticket_number}", response_model=ApiResponse, tags=["Public Tickets"])
async def get_visitor_ticket(
    ticket_number: str,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves full ticket status and public message thread for authorized visitors."""
    res = await db.execute(
        select(Tickets)
        .options(
            selectinload(Tickets.department),
            selectinload(Tickets.messages),
            selectinload(Tickets.status_history),
        )
        .where(Tickets.ticket_number == ticket_number)
    )
    ticket = res.scalars().first()
    if not ticket:
        raise NotFoundError(f"Ticket with identifier '{ticket_number}' not found.")

    # Authorize visitor token or staff token
    is_authorized = await _verify_visitor_ticket_auth(ticket, authorization)
    if not is_authorized:
        raise UnauthorizedError("Ticket tracking requires OTP verification. Please request an access code.")

    # Overdue calculation
    now = datetime.now(timezone.utc)
    is_overdue = (
        ticket.sla_due_at is not None
        and ticket.sla_due_at < now
        and ticket.status not in (TicketStatus.RESOLVED, TicketStatus.CLOSED)
    )

    # Exclude internal staff notes from public visitor view
    public_messages = [
        {
            "id": str(m.id),
            "sender_type": m.sender_type,
            "message": m.message,
            "created_at": m.created_at.isoformat(),
        }
        for m in ticket.messages
        if not m.is_internal_note
    ]

    history_log = [
        {
            "from_status": h.from_status,
            "to_status": h.to_status,
            "change_reason": h.change_reason,
            "created_at": h.created_at.isoformat(),
        }
        for h in ticket.status_history
    ]

    return ApiResponse(
        success=True,
        data={
            "id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "student_name": ticket.student_name,
            "student_email": ticket.student_email,
            "category": ticket.category,
            "subject": ticket.subject,
            "description": ticket.description,
            "status": ticket.status.value,
            "priority": ticket.priority.value,
            "department": ticket.department.name if ticket.department else "General Administration",
            "sla_due_at": ticket.sla_due_at.isoformat() if ticket.sla_due_at else None,
            "is_overdue": is_overdue,
            "resolution_notes": ticket.resolution_notes,
            "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
            "created_at": ticket.created_at.isoformat(),
            "updated_at": ticket.updated_at.isoformat(),
            "messages": public_messages,
            "status_history": history_log,
        },
    )


@public_router.post("/tickets/{ticket_number}/messages", response_model=ApiResponse, tags=["Public Tickets"])
async def visitor_reply_to_ticket(
    ticket_number: str,
    req: TicketMessageCreateRequest,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Allows authorized visitor to reply to an ongoing ticket."""
    res = await db.execute(select(Tickets).where(Tickets.ticket_number == ticket_number))
    ticket = res.scalars().first()
    if not ticket:
        raise NotFoundError(f"Ticket '{ticket_number}' not found.")

    is_authorized = await _verify_visitor_ticket_auth(ticket, authorization)
    if not is_authorized:
        raise UnauthorizedError("Unauthorized. Please verify your OTP to reply.")

    if ticket.status == TicketStatus.CLOSED:
        raise ValidationError("Cannot reply to a closed ticket. Please submit a new support request.")

    # 1. Add student message
    msg = TicketMessages(
        ticket_id=ticket.id,
        sender_type="STUDENT",
        message=req.message.strip(),
        is_internal_note=False,
    )
    db.add(msg)

    # 2. If ticket was WAITING_FOR_USER, transition back to IN_PROGRESS
    old_status = ticket.status
    if ticket.status == TicketStatus.WAITING_FOR_USER:
        ticket.status = TicketStatus.IN_PROGRESS
        ticket.updated_at = datetime.now(timezone.utc)
        history = TicketStatusHistory(
            ticket_id=ticket.id,
            from_status=old_status.value,
            to_status=TicketStatus.IN_PROGRESS.value,
            change_reason="Student replied to ticket message",
        )
        db.add(history)

    await db.commit()

    return ApiResponse(
        success=True,
        data={
            "message_id": str(msg.id),
            "status": ticket.status.value,
            "created_at": msg.created_at.isoformat(),
        },
        message="Reply posted successfully.",
    )


# ── 3. STAFF TICKET MANAGEMENT ENDPOINTS ───────────────────────────────────────

@admin_router.get("/tickets", response_model=ApiResponse, tags=["Admin Tickets"])
async def list_admin_tickets(
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = None,
    priority: Optional[str] = None,
    department_id: Optional[uuid.UUID] = None,
    search: Optional[str] = None,
    overdue_only: bool = False,
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DEPARTMENT_STAFF, UserRole.VIEWER])),
    db: AsyncSession = Depends(get_db),
):
    """Lists tickets with role-based visibility, department scoping, and filtering."""
    query = (
        select(Tickets)
        .options(
            selectinload(Tickets.department),
            selectinload(Tickets.assigned_to_user),
            selectinload(Tickets.messages),
        )
    )

    # Enforce department boundary for Department Staff
    if current_user.role == UserRole.DEPARTMENT_STAFF and current_user.department_id:
        query = query.where(
            or_(
                Tickets.department_id == current_user.department_id,
                Tickets.assigned_to_user_id == current_user.id,
            )
        )

    # Optional department filter for Super Admin / Admin
    if department_id:
        query = query.where(Tickets.department_id == department_id)

    # Status filter
    if status_filter and status_filter.upper() != "ALL":
        query = query.where(Tickets.status == status_filter.upper().strip())

    # Category filter
    if category and category.upper() != "ALL":
        query = query.where(Tickets.category == category.upper().strip())

    # Priority filter
    if priority and priority.upper() != "ALL":
        query = query.where(Tickets.priority == priority.upper().strip())

    # Search keyword
    if search:
        s = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Tickets.ticket_number).like(s),
                func.lower(Tickets.student_name).like(s),
                func.lower(Tickets.student_email).like(s),
                func.lower(Tickets.subject).like(s),
            )
        )

    # Overdue filter
    now = datetime.now(timezone.utc)
    if overdue_only:
        query = query.where(
            Tickets.sla_due_at < now,
            Tickets.status.notin_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
        )

    result = await db.execute(query.order_by(Tickets.created_at.desc()).limit(100))
    tickets = result.scalars().all()

    data = [
        {
            "id": str(t.id),
            "ticket_number": t.ticket_number,
            "student_name": t.student_name,
            "student_email": t.student_email,
            "category": t.category,
            "subject": t.subject,
            "status": t.status.value,
            "priority": t.priority.value,
            "department": t.department.name if t.department else "General Administration",
            "department_id": str(t.department_id) if t.department_id else None,
            "assigned_to": t.assigned_to_user.full_name if t.assigned_to_user else None,
            "assigned_to_user_id": str(t.assigned_to_user_id) if t.assigned_to_user_id else None,
            "sla_due_at": t.sla_due_at.isoformat() if t.sla_due_at else None,
            "is_overdue": (
                t.sla_due_at is not None
                and t.sla_due_at < now
                and t.status not in (TicketStatus.RESOLVED, TicketStatus.CLOSED)
            ),
            "message_count": len(t.messages),
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat(),
        }
        for t in tickets
    ]

    return ApiResponse(success=True, data=data)


@admin_router.get("/tickets/{ticket_id}", response_model=ApiResponse, tags=["Admin Tickets"])
async def get_admin_ticket_detail(
    ticket_id: uuid.UUID,
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DEPARTMENT_STAFF, UserRole.VIEWER])),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves full ticket detail, all messages (including staff internal notes),
    status transition history, and associated chat transcript.
    """
    res = await db.execute(
        select(Tickets)
        .options(
            selectinload(Tickets.department),
            selectinload(Tickets.assigned_to_user),
            selectinload(Tickets.resolved_by),
            selectinload(Tickets.messages).selectinload(TicketMessages.sender_user),
            selectinload(Tickets.status_history).selectinload(TicketStatusHistory.changed_by_user),
        )
        .where(Tickets.id == ticket_id)
    )
    ticket = res.scalars().first()
    if not ticket:
        raise NotFoundError(f"Ticket with ID '{ticket_id}' not found.")

    # Department scope enforcement
    check_department_scope(current_user, ticket.department_id)

    # Conversation reference transcript
    chat_transcript = []
    if ticket.session_id:
        res_msgs = await db.execute(
            select(ChatMessages)
            .where(ChatMessages.session_id == ticket.session_id)
            .order_by(ChatMessages.created_at.asc())
        )
        chat_transcript = [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "confidence_score": m.confidence_score,
                "created_at": m.created_at.isoformat(),
            }
            for m in res_msgs.scalars().all()
        ]

    now = datetime.now(timezone.utc)
    is_overdue = (
        ticket.sla_due_at is not None
        and ticket.sla_due_at < now
        and ticket.status not in (TicketStatus.RESOLVED, TicketStatus.CLOSED)
    )

    messages = [
        {
            "id": str(m.id),
            "sender_type": m.sender_type,
            "sender_name": m.sender_user.full_name if m.sender_user else ticket.student_name,
            "message": m.message,
            "is_internal_note": m.is_internal_note,
            "created_at": m.created_at.isoformat(),
        }
        for m in ticket.messages
    ]

    history_log = [
        {
            "from_status": h.from_status,
            "to_status": h.to_status,
            "changed_by": h.changed_by_user.full_name if h.changed_by_user else "System / Visitor",
            "change_reason": h.change_reason,
            "created_at": h.created_at.isoformat(),
        }
        for h in ticket.status_history
    ]

    return ApiResponse(
        success=True,
        data={
            "id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "session_id": str(ticket.session_id) if ticket.session_id else None,
            "student_name": ticket.student_name,
            "student_email": ticket.student_email,
            "student_phone": ticket.student_phone,
            "category": ticket.category,
            "subject": ticket.subject,
            "description": ticket.description,
            "status": ticket.status.value,
            "priority": ticket.priority.value,
            "department": ticket.department.name if ticket.department else "General Administration",
            "department_id": str(ticket.department_id) if ticket.department_id else None,
            "assigned_to": ticket.assigned_to_user.full_name if ticket.assigned_to_user else None,
            "assigned_to_user_id": str(ticket.assigned_to_user_id) if ticket.assigned_to_user_id else None,
            "sla_due_at": ticket.sla_due_at.isoformat() if ticket.sla_due_at else None,
            "is_overdue": is_overdue,
            "resolution_notes": ticket.resolution_notes,
            "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
            "resolved_by": ticket.resolved_by.full_name if ticket.resolved_by else None,
            "created_at": ticket.created_at.isoformat(),
            "updated_at": ticket.updated_at.isoformat(),
            "messages": messages,
            "status_history": history_log,
            "chat_transcript": chat_transcript,
        },
    )


@admin_router.post("/tickets/{ticket_id}/assign", response_model=ApiResponse, tags=["Admin Tickets"])
async def assign_ticket_staff(
    ticket_id: uuid.UUID,
    req: TicketAssignRequest,
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DEPARTMENT_STAFF])),
    db: AsyncSession = Depends(get_db),
):
    """Assigns staff member to ticket and advances status to ASSIGNED if previously OPEN."""
    ticket = await db.get(Tickets, ticket_id)
    if not ticket:
        raise NotFoundError(f"Ticket '{ticket_id}' not found.")

    check_department_scope(current_user, ticket.department_id)

    target_user = await db.get(Users, req.assigned_to_user_id)
    if not target_user or not target_user.is_active:
        raise NotFoundError("Assigned staff member not found or is deactivated.")

    old_status = ticket.status
    ticket.assigned_to_user_id = target_user.id
    ticket.updated_at = datetime.now(timezone.utc)

    # Automatic state transition if OPEN
    if ticket.status == TicketStatus.OPEN:
        ticket.status = TicketStatus.ASSIGNED

    # History entry
    history = TicketStatusHistory(
        ticket_id=ticket.id,
        from_status=old_status.value,
        to_status=ticket.status.value,
        changed_by_user_id=current_user.id,
        change_reason=f"Assigned to {target_user.full_name}. {req.notes or ''}".strip(),
    )
    db.add(history)

    await db.commit()

    return ApiResponse(
        success=True,
        data={
            "ticket_id": str(ticket.id),
            "assigned_to": target_user.full_name,
            "status": ticket.status.value,
        },
        message=f"Ticket assigned to {target_user.full_name}.",
    )


@admin_router.patch("/tickets/{ticket_id}/status", response_model=ApiResponse, tags=["Admin Tickets"])
async def update_ticket_status(
    ticket_id: uuid.UUID,
    req: TicketStatusUpdateRequest,
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DEPARTMENT_STAFF])),
    db: AsyncSession = Depends(get_db),
):
    """Validates and executes a status lifecycle transition."""
    ticket = await db.get(Tickets, ticket_id)
    if not ticket:
        raise NotFoundError(f"Ticket '{ticket_id}' not found.")

    check_department_scope(current_user, ticket.department_id)

    try:
        new_status = TicketStatus(req.status.upper().strip())
    except ValueError:
        raise ValidationError(f"Invalid status value '{req.status}'. Allowed: {[s.value for s in TicketStatus]}")

    if new_status == ticket.status:
        return ApiResponse(success=True, message=f"Ticket is already in status '{ticket.status.value}'.")

    # Validate transition state machine
    allowed = VALID_STATUS_TRANSITIONS.get(ticket.status, set())
    if new_status not in allowed:
        raise ValidationError(
            f"Invalid transition from '{ticket.status.value}' to '{new_status.value}'. Allowed transitions: {[s.value for s in allowed]}"
        )

    # Resolution check
    if new_status == TicketStatus.RESOLVED and not req.resolution_notes:
        raise ValidationError("Resolution information is required when marking a ticket as RESOLVED.")

    old_status = ticket.status
    ticket.status = new_status
    ticket.updated_at = datetime.now(timezone.utc)

    if new_status == TicketStatus.RESOLVED:
        ticket.resolved_at = datetime.now(timezone.utc)
        ticket.resolved_by_id = current_user.id
        ticket.resolution_notes = req.resolution_notes.strip()

    history = TicketStatusHistory(
        ticket_id=ticket.id,
        from_status=old_status.value,
        to_status=new_status.value,
        changed_by_user_id=current_user.id,
        change_reason=req.reason or req.resolution_notes or "Status update by staff",
    )
    db.add(history)

    await db.commit()

    # Visitor notification
    if new_status == TicketStatus.RESOLVED:
        await email_service.notify_ticket_resolved(
            ticket_number=ticket.ticket_number,
            student_name=ticket.student_name,
            student_email=ticket.student_email,
            resolution_notes=ticket.resolution_notes,
        )
    else:
        await email_service.notify_status_changed(
            ticket_number=ticket.ticket_number,
            student_name=ticket.student_name,
            student_email=ticket.student_email,
            old_status=old_status.value,
            new_status=new_status.value,
            reason=req.reason,
        )

    return ApiResponse(
        success=True,
        data={
            "ticket_id": str(ticket.id),
            "from_status": old_status.value,
            "status": new_status.value,
            "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
        },
        message=f"Status transitioned to '{new_status.value}'.",
    )


@admin_router.post("/tickets/{ticket_id}/messages", response_model=ApiResponse, tags=["Admin Tickets"])
async def add_staff_ticket_message(
    ticket_id: uuid.UUID,
    req: TicketMessageCreateRequest,
    current_user: Users = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DEPARTMENT_STAFF])),
    db: AsyncSession = Depends(get_db),
):
    """Allows staff to post internal notes (staff-only) or direct responses to the visitor."""
    ticket = await db.get(Tickets, ticket_id)
    if not ticket:
        raise NotFoundError(f"Ticket '{ticket_id}' not found.")

    check_department_scope(current_user, ticket.department_id)

    msg = TicketMessages(
        ticket_id=ticket.id,
        sender_type="STAFF",
        sender_user_id=current_user.id,
        message=req.message.strip(),
        is_internal_note=req.is_internal_note,
    )
    db.add(msg)
    ticket.updated_at = datetime.now(timezone.utc)

    # If replying to visitor, auto-update to WAITING_FOR_USER if in progress
    if not req.is_internal_note and ticket.status in (TicketStatus.IN_PROGRESS, TicketStatus.ASSIGNED):
        old_status = ticket.status
        ticket.status = TicketStatus.WAITING_FOR_USER
        history = TicketStatusHistory(
            ticket_id=ticket.id,
            from_status=old_status.value,
            to_status=TicketStatus.WAITING_FOR_USER.value,
            changed_by_user_id=current_user.id,
            change_reason="Staff responded to student inquiry",
        )
        db.add(history)

    await db.commit()

    # Dispatch email notification if not an internal note
    if not req.is_internal_note:
        await email_service.notify_staff_replied(
            ticket_number=ticket.ticket_number,
            student_name=ticket.student_name,
            student_email=ticket.student_email,
            staff_name=current_user.full_name,
            message_text=req.message.strip(),
        )

    return ApiResponse(
        success=True,
        data={
            "message_id": str(msg.id),
            "is_internal_note": msg.is_internal_note,
            "status": ticket.status.value,
            "created_at": msg.created_at.isoformat(),
        },
        message="Internal note saved." if req.is_internal_note else "Response dispatched to visitor.",
    )
