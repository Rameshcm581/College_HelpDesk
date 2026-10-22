"""initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-22 12:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable required PostgreSQL extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\";")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"vector\";")

    # 2. Create Enums idempotently
    op.execute("""
    DO $$ BEGIN
        CREATE TYPE user_role_enum AS ENUM ('SUPER_ADMIN', 'CONTENT_APPROVER', 'SUPPORT_AGENT', 'AUDITOR');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """)

    op.execute("""
    DO $$ BEGIN
        CREATE TYPE document_status_enum AS ENUM ('DRAFT', 'PENDING_REVIEW', 'APPROVED', 'PUBLISHED', 'ARCHIVED');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """)

    op.execute("""
    DO $$ BEGIN
        CREATE TYPE ticket_priority_enum AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'URGENT');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """)

    op.execute("""
    DO $$ BEGIN
        CREATE TYPE ticket_status_enum AS ENUM ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """)

    user_role_type = postgresql.ENUM('SUPER_ADMIN', 'CONTENT_APPROVER', 'SUPPORT_AGENT', 'AUDITOR', name='user_role_enum', create_type=False)
    doc_status_type = postgresql.ENUM('DRAFT', 'PENDING_REVIEW', 'APPROVED', 'PUBLISHED', 'ARCHIVED', name='document_status_enum', create_type=False)
    ticket_priority_type = postgresql.ENUM('LOW', 'MEDIUM', 'HIGH', 'URGENT', name='ticket_priority_enum', create_type=False)
    ticket_status_type = postgresql.ENUM('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED', name='ticket_status_enum', create_type=False)

    # 3. Create departments table
    op.create_table(
        'departments',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('contact_email', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_departments_code'), 'departments', ['code'], unique=True)

    # 4. Create academic_years table
    op.create_table(
        'academic_years',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('is_current', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_academic_years_code'), 'academic_years', ['code'], unique=True)

    # 5. Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', user_role_type, server_default='SUPPORT_AGENT', nullable=False),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 6. Create documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('storage_path', sa.String(length=1024), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('checksum_sha256', sa.String(length=64), nullable=False),
        sa.Column('version_number', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('status', doc_status_type, server_default='DRAFT', nullable=False),
        sa.Column('academic_year_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('uploaded_by_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('approved_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['academic_year_id'], ['academic_years.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_documents_checksum', 'documents', ['checksum_sha256'], unique=False)
    op.create_index('idx_documents_department', 'documents', ['department_id'], unique=False)
    op.create_index('idx_documents_status_academic_year', 'documents', ['status', 'academic_year_id'], unique=False)

    # 7. Create document_versions table
    op.create_table(
        'document_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.Column('storage_path', sa.String(length=1024), nullable=False),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 8. Create document_chunks table with Vector(1536) and TSVector
    op.create_table(
        'document_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=False),
        sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
        sa.Column('chunk_metadata', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'chunk_index', name='uq_document_chunk_index')
    )
    op.create_index(op.f('ix_document_chunks_document_id'), 'document_chunks', ['document_id'], unique=False)
    op.execute("CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw ON document_chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_chunks_search_vector_gin ON document_chunks USING gin (search_vector);")

    # 9. Create chat_sessions table
    op.create_table(
        'chat_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('ip_hash', sa.String(length=64), nullable=False),
        sa.Column('language_code', sa.String(length=10), server_default='en', nullable=False),
        sa.Column('client_origin', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('last_active_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 10. Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('language_code', sa.String(length=10), server_default='en', nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('retrieved_chunk_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), server_default=sa.text('0'), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), server_default=sa.text('0'), nullable=True),
        sa.Column('latency_ms', sa.Integer(), server_default=sa.text('0'), nullable=True),
        sa.Column('user_feedback', sa.String(length=20), server_default='none', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_messages_session_id'), 'chat_messages', ['session_id'], unique=False)

    # 11. Create tickets table
    op.create_table(
        'tickets',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('ticket_number', sa.String(length=30), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('student_name', sa.String(length=150), nullable=False),
        sa.Column('student_email', sa.String(length=255), nullable=False),
        sa.Column('student_phone', sa.String(length=30), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('priority', ticket_priority_type, server_default='MEDIUM', nullable=False),
        sa.Column('status', ticket_status_type, server_default='OPEN', nullable=False),
        sa.Column('assigned_to_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['assigned_to_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticket_number')
    )
    op.create_index(op.f('ix_tickets_department_id'), 'tickets', ['department_id'], unique=False)
    op.create_index(op.f('ix_tickets_status'), 'tickets', ['status'], unique=False)
    op.create_index(op.f('ix_tickets_student_email'), 'tickets', ['student_email'], unique=False)
    op.create_index(op.f('ix_tickets_ticket_number'), 'tickets', ['ticket_number'], unique=True)

    # 12. Create ticket_messages table
    op.create_table(
        'ticket_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('ticket_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_type', sa.String(length=20), nullable=False),
        sa.Column('sender_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_internal_note', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('attachment_urls', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['sender_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ticket_messages_ticket_id'), 'ticket_messages', ['ticket_id'], unique=False)

    # 13. Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_name', sa.String(length=100), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('old_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('new_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)

    # 14. Create api_usage_metrics table
    op.create_table(
        'api_usage_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('metric_date', sa.Date(), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('total_requests', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('total_prompt_tokens', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('total_completion_tokens', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('estimated_cost_usd', sa.Numeric(precision=10, scale=4), server_default=sa.text('0.0000'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_usage_metrics_metric_date'), 'api_usage_metrics', ['metric_date'], unique=False)

    # 15. Seed baseline Academic Year & Department
    op.execute("""
        INSERT INTO academic_years (id, code, start_date, end_date, is_current)
        VALUES (gen_random_uuid(), '2025-2026', '2025-06-01', '2026-05-31', true)
        ON CONFLICT (code) DO NOTHING;
    """)

    op.execute("""
        INSERT INTO departments (id, code, name, contact_email, is_active)
        VALUES 
            (gen_random_uuid(), 'ADM', 'Admissions Cell', 'admissions@college.edu', true),
            (gen_random_uuid(), 'HST', 'Hostel Administration', 'hostel@college.edu', true),
            (gen_random_uuid(), 'EXM', 'Examination Cell', 'coe@college.edu', true),
            (gen_random_uuid(), 'ACA', 'Academic Affairs', 'academics@college.edu', true)
        ON CONFLICT (code) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_table('api_usage_metrics')
    op.drop_table('audit_logs')
    op.drop_table('ticket_messages')
    op.drop_table('tickets')
    op.drop_table('chat_messages')
    op.drop_table('chat_sessions')
    op.drop_table('document_chunks')
    op.drop_table('document_versions')
    op.drop_table('documents')
    op.drop_table('users')
    op.drop_table('academic_years')
    op.drop_table('departments')

    op.execute("DROP TYPE IF EXISTS ticket_status_enum;")
    op.execute("DROP TYPE IF EXISTS ticket_priority_enum;")
    op.execute("DROP TYPE IF EXISTS document_status_enum;")
    op.execute("DROP TYPE IF EXISTS user_role_enum;")
