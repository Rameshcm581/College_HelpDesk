"""document_versioning_and_ingestion

Revision ID: 0002_doc_versioning
Revises: 0001_initial_schema
Create Date: 2026-10-22 16:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0002_doc_versioning'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Commit before adding new enum values and commit after
    op.execute("COMMIT;")
    op.execute("ALTER TYPE document_status_enum ADD VALUE IF NOT EXISTS 'UPLOADED';")
    op.execute("ALTER TYPE document_status_enum ADD VALUE IF NOT EXISTS 'PROCESSING';")
    op.execute("ALTER TYPE document_status_enum ADD VALUE IF NOT EXISTS 'REVIEW_REQUIRED';")
    op.execute("ALTER TYPE document_status_enum ADD VALUE IF NOT EXISTS 'INDEXING';")
    op.execute("ALTER TYPE document_status_enum ADD VALUE IF NOT EXISTS 'ACTIVE';")
    op.execute("ALTER TYPE document_status_enum ADD VALUE IF NOT EXISTS 'FAILED';")
    op.execute("BEGIN;")

    # 2. Create job_status_enum
    op.execute("""
    DO $$ BEGIN
        CREATE TYPE job_status_enum AS ENUM ('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """)

    # 3. Add columns to document_versions
    op.add_column('document_versions', sa.Column('file_name', sa.String(255), nullable=False, server_default=''))
    op.add_column('document_versions', sa.Column('mime_type', sa.String(100), nullable=False, server_default='application/pdf'))
    op.add_column('document_versions', sa.Column('file_size_bytes', sa.Integer(), nullable=False, server_default=sa.text('0')))
    op.add_column('document_versions', sa.Column('checksum_sha256', sa.String(64), nullable=False, server_default=''))
    op.add_column('document_versions', sa.Column('status', postgresql.ENUM('UPLOADED', 'PROCESSING', 'REVIEW_REQUIRED', 'APPROVED', 'INDEXING', 'ACTIVE', 'FAILED', 'ARCHIVED', 'DRAFT', 'PENDING_REVIEW', 'PUBLISHED', name='document_status_enum', create_type=False), nullable=False, server_default='DRAFT'))
    op.add_column('document_versions', sa.Column('valid_from', sa.Date(), nullable=True))
    op.add_column('document_versions', sa.Column('valid_until', sa.Date(), nullable=True))
    op.add_column('document_versions', sa.Column('approved_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))
    op.add_column('document_versions', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('document_versions', sa.Column('extracted_text_preview', sa.Text(), nullable=True))
    op.add_column('document_versions', sa.Column('page_count', sa.Integer(), nullable=False, server_default=sa.text('0')))
    op.add_column('document_versions', sa.Column('chunk_count', sa.Integer(), nullable=False, server_default=sa.text('0')))
    op.add_column('document_versions', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))

    # Update default to UPLOADED
    op.execute("ALTER TABLE document_versions ALTER COLUMN status SET DEFAULT 'UPLOADED';")

    op.create_index('idx_doc_versions_doc_version', 'document_versions', ['document_id', 'version_number'], unique=True)
    op.create_index('idx_doc_versions_status', 'document_versions', ['status'])
    op.create_index('idx_doc_versions_checksum', 'document_versions', ['checksum_sha256'])

    # 4. Add active_version_id to documents
    op.add_column('documents', sa.Column('active_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('document_versions.id', ondelete='SET NULL'), nullable=True))

    # 5. Add version_id to document_chunks
    op.add_column('document_chunks', sa.Column('version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('document_versions.id', ondelete='CASCADE'), nullable=True))
    op.create_index('idx_chunks_version_id', 'document_chunks', ['version_id'])

    # 6. Create ingestion_jobs table
    op.create_table(
        'ingestion_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=True),
        sa.Column('version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('document_versions.id', ondelete='CASCADE'), nullable=True),
        sa.Column('job_type', sa.String(50), nullable=False, server_default='PDF_UPLOAD'),
        sa.Column('source_url', sa.String(2048), nullable=True),
        sa.Column('status', postgresql.ENUM('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED', name='job_status_enum', create_type=False), nullable=False, server_default='QUEUED'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default=sa.text('3')),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('job_metadata', postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_ingestion_jobs_status', 'ingestion_jobs', ['status'])
    op.create_index('idx_ingestion_jobs_doc_id', 'ingestion_jobs', ['document_id'])
    op.create_index('idx_ingestion_jobs_version_id', 'ingestion_jobs', ['version_id'])

    # 7. Backfill existing documents and versions
    op.execute("""
    DO $$
    DECLARE
        doc_rec RECORD;
        v_id UUID;
    BEGIN
        FOR doc_rec IN SELECT * FROM documents LOOP
            SELECT id INTO v_id FROM document_versions WHERE document_id = doc_rec.id AND version_number = doc_rec.version_number;
            IF v_id IS NULL THEN
                v_id := gen_random_uuid();
                INSERT INTO document_versions (
                    id, document_id, version_number, file_name, storage_path, mime_type, file_size_bytes, checksum_sha256,
                    status, change_summary, created_by_id, approved_by_id, approved_at, page_count, chunk_count, created_at, updated_at
                ) VALUES (
                    v_id, doc_rec.id, doc_rec.version_number, doc_rec.file_name, doc_rec.storage_path, doc_rec.mime_type,
                    doc_rec.file_size_bytes, doc_rec.checksum_sha256, doc_rec.status, 'Initial version', doc_rec.uploaded_by_id,
                    doc_rec.approved_by_id, doc_rec.approved_at, 3, 3, doc_rec.created_at, doc_rec.updated_at
                );
            END IF;
            UPDATE documents SET active_version_id = v_id WHERE id = doc_rec.id;
            UPDATE document_chunks SET version_id = v_id WHERE document_id = doc_rec.id AND version_id IS NULL;
        END LOOP;
    END $$;
    """)


def downgrade() -> None:
    op.drop_table('ingestion_jobs')
    op.drop_index('idx_chunks_version_id', table_name='document_chunks')
    op.drop_column('document_chunks', 'version_id')
    op.drop_column('documents', 'active_version_id')
    op.drop_index('idx_doc_versions_checksum', table_name='document_versions')
    op.drop_index('idx_doc_versions_status', table_name='document_versions')
    op.drop_index('idx_doc_versions_doc_version', table_name='document_versions')
    op.drop_column('document_versions', 'updated_at')
    op.drop_column('document_versions', 'chunk_count')
    op.drop_column('document_versions', 'page_count')
    op.drop_column('document_versions', 'extracted_text_preview')
    op.drop_column('document_versions', 'approved_at')
    op.drop_column('document_versions', 'approved_by_id')
    op.drop_column('document_versions', 'valid_until')
    op.drop_column('document_versions', 'valid_from')
    op.drop_column('document_versions', 'status')
    op.drop_column('document_versions', 'checksum_sha256')
    op.drop_column('document_versions', 'file_size_bytes')
    op.drop_column('document_versions', 'mime_type')
    op.drop_column('document_versions', 'file_name')
    op.execute("DROP TYPE IF EXISTS job_status_enum;")
