# backend/Services/HelpdeskService/tests/test_models.py
import pytest
from models import Base
from models.models import (
    AcademicYears,
    ChatMessages,
    ChatSessions,
    Departments,
    DocumentChunks,
    Documents,
    Tickets,
    Users,
)


def test_models_metadata_registration():
    """Verifies that all core tables are properly registered in SQLAlchemy Base.metadata."""
    tables = Base.metadata.tables.keys()
    required_tables = [
        "users",
        "departments",
        "academic_years",
        "documents",
        "document_versions",
        "document_chunks",
        "chat_sessions",
        "chat_messages",
        "tickets",
        "ticket_messages",
        "audit_logs",
        "api_usage_metrics",
        "ingestion_jobs",
    ]

    for table in required_tables:
        assert table in tables, f"Table '{table}' missing from Base.metadata"


def test_chunk_embedding_vector_dimension():
    """Verifies that document_chunks embedding vector is defined with dimension 1536."""
    chunk_table = Base.metadata.tables["document_chunks"]
    embedding_col = chunk_table.columns["embedding"]
    assert embedding_col.type.dim == 1536
