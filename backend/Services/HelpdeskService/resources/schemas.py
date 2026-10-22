# backend/Services/HelpdeskService/resources/schemas.py
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ── BASE ENVELOPE ─────────────────────────────────────────────────────────────

class ApiResponse(BaseModel):
    success: bool = True
    data: Optional[Any] = None
    message: Optional[str] = None


class ApiError(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None
    timestamp: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ApiError


# ── HEALTH ────────────────────────────────────────────────────────────────────

class DatabaseHealth(BaseModel):
    status: str
    pgvector_installed: bool


class RedisHealth(BaseModel):
    status: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    database: DatabaseHealth
    redis: RedisHealth
    timestamp: str


# ── AUTH ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserSummary(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    department_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserSummary


# ── PUBLIC CHAT & CITATIONS ───────────────────────────────────────────────────

class ChatQueryRequest(BaseModel):
    session_id: Optional[UUID] = None
    query: str = Field(..., min_length=2, max_length=1000)
    language: str = Field(default="en", pattern="^(en|ta|ta-Latn)$")
    academic_year: Optional[str] = None
    department_id: Optional[UUID] = None
    department_code: Optional[str] = None
    document_type: Optional[str] = None
    version_number: Optional[int] = None


class CitationItem(BaseModel):
    document_id: UUID
    document_title: str
    version_number: int
    academic_year: str
    page_number: int
    section: Optional[str] = None
    snippet: Optional[str] = None


class SuggestedTicket(BaseModel):
    default_category: str
    prefilled_query: str


class ChatQueryResponse(BaseModel):
    message_id: UUID
    session_id: UUID
    response: str
    language: str
    confidence_score: float
    fallback_triggered: bool
    citations: List[CitationItem] = []
    suggested_ticket: Optional[SuggestedTicket] = None


class ChatFeedbackRequest(BaseModel):
    message_id: UUID
    feedback: str = Field(..., pattern="^(helpful|unhelpful)$")
    comments: Optional[str] = None


# ── TICKETS ───────────────────────────────────────────────────────────────────

# ── TICKETS ───────────────────────────────────────────────────────────────────

class TicketCreateRequest(BaseModel):
    session_id: Optional[UUID] = None
    student_name: str = Field(..., min_length=2, max_length=150)
    student_email: EmailStr
    student_phone: Optional[str] = None
    category: str = Field(default="GENERAL")
    priority: str = Field(default="MEDIUM")
    subject: Optional[str] = Field(default=None, max_length=255)
    message: str = Field(..., min_length=5, max_length=5000)
    include_chat_history: bool = True


class TicketOtpRequest(BaseModel):
    email: EmailStr


class TicketOtpVerifyRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class TicketStatusUpdateRequest(BaseModel):
    status: str
    reason: Optional[str] = None
    resolution_notes: Optional[str] = None


class TicketAssignRequest(BaseModel):
    assigned_to_user_id: UUID
    notes: Optional[str] = None


class TicketMessageCreateRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    is_internal_note: bool = False
    attachment_urls: List[str] = []


class TicketResponse(BaseModel):
    id: UUID
    ticket_number: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── DOCUMENT INGESTION & MANAGEMENT ──────────────────────────────────────────

class UrlIngestRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=2048)
    title: Optional[str] = Field(default=None, max_length=255)
    academic_year_code: str = Field(default="2025-2026")
    department_code: str = Field(default="GENERAL")
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None


class DocumentApprovalRequest(BaseModel):
    comments: Optional[str] = None


class DocumentRejectRequest(BaseModel):
    reason: str = Field(..., min_length=2, max_length=1000)


class DocumentVersionSummary(BaseModel):
    id: UUID
    version_number: int
    file_name: str
    status: str
    page_count: int
    chunk_count: int
    checksum_sha256: str
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    change_summary: Optional[str] = None
    created_at: str
    approved_at: Optional[str] = None


class DocumentDetailResponse(BaseModel):
    id: UUID
    title: str
    file_name: str
    status: str
    active_version_id: Optional[UUID] = None
    version_number: int
    department_id: UUID
    academic_year_id: UUID
    versions: List[DocumentVersionSummary] = []

