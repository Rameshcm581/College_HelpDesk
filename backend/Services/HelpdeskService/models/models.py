# backend/Services/HelpdeskService/models/models.py
import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from models import Base

_UUID_DEFAULT = text("gen_random_uuid()")


# ── ENUMS ──────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    DEPARTMENT_STAFF = "DEPARTMENT_STAFF"
    VIEWER = "VIEWER"
    # Backward compatibility aliases
    CONTENT_APPROVER = "CONTENT_APPROVER"
    SUPPORT_AGENT = "SUPPORT_AGENT"
    AUDITOR = "AUDITOR"


class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DocumentStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED = "APPROVED"
    INDEXING = "INDEXING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"
    # Backward compatibility aliases
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    PUBLISHED = "PUBLISHED"


class TicketPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TicketStatus(str, enum.Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_USER = "WAITING_FOR_USER"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class TicketCategory(str, enum.Enum):
    ADMISSIONS = "ADMISSIONS"
    FEES = "FEES"
    EXAMINATIONS = "EXAMINATIONS"
    HOSTEL = "HOSTEL"
    SCHOLARSHIPS = "SCHOLARSHIPS"
    PLACEMENTS = "PLACEMENTS"
    GENERAL = "GENERAL"


# ── MODELS ─────────────────────────────────────────────────────────────────────

class Departments(Base):
    __tablename__ = "departments"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_DEFAULT)
    code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(150), nullable=False)
    contact_email = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    users = relationship("Users", back_populates="department")
    documents = relationship("Documents", back_populates="department")
    tickets = relationship("Tickets", back_populates="department")


class AcademicYears(Base):
    __tablename__ = "academic_years"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_DEFAULT)
    code = Column(String(20), nullable=False, unique=True, index=True)  # e.g. "2025-2026"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_current = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    documents = relationship("Documents", back_populates="academic_year")


class Users(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_DEFAULT)
    email = Column(String(255), nullable=False, unique=True, index=True)
    full_name = Column(String(150), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole, name="user_role_enum"), nullable=False, server_default=UserRole.SUPPORT_AGENT.value)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"), onupdate=datetime.now(timezone.utc))

    # Relationships
    department = relationship("Departments", back_populates="users")
    uploaded_documents = relationship("Documents", foreign_keys="Documents.uploaded_by_id", back_populates="uploaded_by")
    approved_documents = relationship("Documents", foreign_keys="Documents.approved_by_id", back_populates="approved_by")
    assigned_tickets = relationship("Tickets", foreign_keys="Tickets.assigned_to_user_id", back_populates="assigned_to_user")


class Documents(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_DEFAULT)
    title = Column(String(255), nullable=False)
    file_name = Column(String(255), nullable=False)
    storage_path = Column(String(1024), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    checksum_sha256 = Column(String(64), nullable=False, index=True)
    version_number = Column(Integer, nullable=False, server_default=text("1"))
    status = Column(Enum(DocumentStatus, name="document_status_enum"), nullable=False, server_default=DocumentStatus.UPLOADED.value)
    document_type = Column(String(50), nullable=False, server_default="REGULATION", index=True)
    language_code = Column(String(10), nullable=False, server_default="en", index=True)
    academic_year_id = Column(UUID(as_uuid=True), ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)
    uploaded_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    approved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    active_version_id = Column(UUID(as_uuid=True), ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"), onupdate=datetime.now(timezone.utc))

    # Relationships
    department = relationship("Departments", back_populates="documents")
    academic_year = relationship("AcademicYears", back_populates="documents")
    uploaded_by = relationship("Users", foreign_keys=[uploaded_by_id], back_populates="uploaded_documents")
    approved_by = relationship("Users", foreign_keys=[approved_by_id], back_populates="approved_documents")
    active_version = relationship("DocumentVersions", foreign_keys=[active_version_id], post_update=True)
    chunks = relationship("DocumentChunks", back_populates="document", cascade="all, delete-orphan")
    versions = relationship("DocumentVersions", foreign_keys="DocumentVersions.document_id", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_documents_status_academic_year", "status", "academic_year_id"),
        Index("idx_documents_department", "department_id"),
        Index("idx_documents_filtering", "status", "academic_year_id", "department_id", "document_type", "language_code"),
    )


class DocumentVersions(Base):
    __tablename__ = "document_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_DEFAULT)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    file_name = Column(String(255), nullable=False, server_default="")
    storage_path = Column(String(1024), nullable=False)
    mime_type = Column(String(100), nullable=False, server_default="application/pdf")
    file_size_bytes = Column(Integer, nullable=False, server_default=text("0"))
    checksum_sha256 = Column(String(64), nullable=False, server_default="", index=True)
    status = Column(Enum(DocumentStatus, name="document_status_enum"), nullable=False, server_default=DocumentStatus.UPLOADED.value)
    document_type = Column(String(50), nullable=False, server_default="REGULATION", index=True)
    language_code = Column(String(10), nullable=False, server_default="en", index=True)
    change_summary = Column(Text, nullable=True)
    valid_from = Column(Date, nullable=True)
    valid_until = Column(Date, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    extracted_text_preview = Column(Text, nullable=True)
    page_count = Column(Integer, nullable=False, server_default=text("0"))
    chunk_count = Column(Integer, nullable=False, server_default=text("0"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"), onupdate=datetime.now(timezone.utc))

    # Relationships
    document = relationship("Documents", foreign_keys=[document_id], back_populates="versions")
    created_by = relationship("Users", foreign_keys=[created_by_id])
    approved_by = relationship("Users", foreign_keys=[approved_by_id])
    chunks = relationship("DocumentChunks", back_populates="version", cascade="all, delete-orphan")
    ingestion_jobs = relationship("IngestionJobs", back_populates="version", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_doc_versions_doc_version", "document_id", "version_number", unique=True),
        Index("idx_doc_versions_status", "status"),
    )


class DocumentChunks(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_DEFAULT)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(UUID(as_uuid=True), ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=True, index=True)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=False)
    embedding = Column(Vector(1536), nullable=False)
    search_vector = Column(TSVECTOR, nullable=True)
    chunk_metadata = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    document = relationship("Documents", back_populates="chunks")
    version = relationship("DocumentVersions", back_populates="chunks")

    __table_args__ = (
        Index("idx_chunks_search_vector_gin", "search_vector", postgresql_using="gin"),
        Index("idx_chunks_version_id", "version_id"),
    )


class IngestionJobs(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_DEFAULT)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True)
    version_id = Column(UUID(as_uuid=True), ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=True, index=True)
    job_type = Column(String(50), nullable=False, default="PDF_UPLOAD")  # 'PDF_UPLOAD', 'WEBSITE_URL', 'INDEXING'
    source_url = Column(String(2048), nullable=True)
    status = Column(Enum(JobStatus, name="job_status_enum"), nullable=False, server_default=JobStatus.QUEUED.value, index=True)
    retry_count = Column(Integer, nullable=False, server_default=text("0"))
    max_retries = Column(Integer, nullable=False, server_default=text("3"))
    error_message = Column(Text, nullable=True)
    job_metadata = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"), onupdate=datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    document = relationship("Documents")
    version = relationship("DocumentVersions", back_populates="ingestion_jobs")


class ChatSessions(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_DEFAULT)
    ip_hash = Column(String(64), nullable=False)
    language_code = Column(String(10), nullable=False, server_default="en")
    client_origin = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    last_active_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    messages = relationship("ChatMessages", back_populates="session", cascade="all, delete-orphan")
    tickets = relationship("Tickets", back_populates="session")


class ChatMessages(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_DEFAULT)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    language_code = Column(String(10), nullable=False, server_default="en")
    confidence_score = Column(Float, nullable=True)
    retrieved_chunk_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    prompt_tokens = Column(Integer, server_default=text("0"))
    completion_tokens = Column(Integer, server_default=text("0"))
    latency_ms = Column(Integer, server_default=text("0"))
    user_feedback = Column(String(20), server_default="none")  # 'helpful', 'unhelpful', 'none'
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    session = relationship("ChatSessions", back_populates="messages")


class Tickets(Base):
    __tablename__ = "tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_DEFAULT)
    ticket_number = Column(String(30), nullable=False, unique=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    student_name = Column(String(150), nullable=False)
    student_email = Column(String(255), nullable=False, index=True)
    student_phone = Column(String(30), nullable=True)
    category = Column(String(50), nullable=False)
    priority = Column(Enum(TicketPriority, name="ticket_priority_enum"), nullable=False, server_default=TicketPriority.MEDIUM.value)
    status = Column(Enum(TicketStatus, name="ticket_status_enum"), nullable=False, server_default=TicketStatus.OPEN.value, index=True)
    assigned_to_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    subject = Column(String(255), nullable=False, server_default="")
    description = Column(Text, nullable=False, server_default="")
    sla_due_at = Column(DateTime(timezone=True), nullable=True, index=True)
    resolved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"), onupdate=datetime.now(timezone.utc))

    # Relationships
    department = relationship("Departments", back_populates="tickets")
    session = relationship("ChatSessions", back_populates="tickets")
    assigned_to_user = relationship("Users", foreign_keys=[assigned_to_user_id], back_populates="assigned_tickets")
    resolved_by = relationship("Users", foreign_keys=[resolved_by_id])
    messages = relationship("TicketMessages", back_populates="ticket", cascade="all, delete-orphan", order_by="TicketMessages.created_at.asc()")
    status_history = relationship("TicketStatusHistory", back_populates="ticket", cascade="all, delete-orphan", order_by="TicketStatusHistory.created_at.asc()")
    otps = relationship("TicketOtps", back_populates="ticket", cascade="all, delete-orphan")


class TicketMessages(Base):
    __tablename__ = "ticket_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_DEFAULT)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_type = Column(String(20), nullable=False)  # 'STUDENT', 'STAFF', 'SYSTEM'
    sender_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    message = Column(Text, nullable=False)
    is_internal_note = Column(Boolean, nullable=False, server_default=text("false"))
    attachment_urls = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    # Relationships
    ticket = relationship("Tickets", back_populates="messages")
    sender_user = relationship("Users", foreign_keys=[sender_user_id])


class TicketStatusHistory(Base):
    __tablename__ = "ticket_status_history"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_DEFAULT)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status = Column(String(50), nullable=False)
    to_status = Column(String(50), nullable=False)
    changed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    change_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    ticket = relationship("Tickets", back_populates="status_history")
    changed_by_user = relationship("Users", foreign_keys=[changed_by_user_id])


class TicketOtps(Base):
    __tablename__ = "ticket_otps"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_DEFAULT)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    otp_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, nullable=False, server_default=text("0"))
    max_attempts = Column(Integer, nullable=False, server_default=text("3"))
    is_used = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    ticket = relationship("Tickets", back_populates="otps")


class AuditLogs(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_DEFAULT)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    entity_name = Column(String(100), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    ip_address = Column(String(45), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"), index=True)


class ApiUsageMetrics(Base):
    __tablename__ = "api_usage_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_DEFAULT)
    metric_date = Column(Date, nullable=False, index=True)
    model_name = Column(String(100), nullable=False)
    total_requests = Column(Integer, nullable=False, server_default=text("0"))
    total_prompt_tokens = Column(Integer, nullable=False, server_default=text("0"))
    total_completion_tokens = Column(Integer, nullable=False, server_default=text("0"))
    estimated_cost_usd = Column(Numeric(10, 4), nullable=False, server_default=text("0.0000"))


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=_UUID_DEFAULT)
    key = Column(String(100), nullable=False, unique=True, index=True)
    value = Column(JSONB, nullable=False)
    description = Column(Text, nullable=True)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"), onupdate=datetime.now(timezone.utc))

