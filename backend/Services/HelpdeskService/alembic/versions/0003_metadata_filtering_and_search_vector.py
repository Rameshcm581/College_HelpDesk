"""metadata_filtering_and_search_vector

Revision ID: 0003_metadata_search
Revises: 0002_doc_versioning
Create Date: 2026-10-22 17:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0003_metadata_search'
down_revision: Union[str, None] = '0002_doc_versioning'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add document_type and language_code to documents
    op.add_column('documents', sa.Column('document_type', sa.String(50), nullable=False, server_default='REGULATION'))
    op.add_column('documents', sa.Column('language_code', sa.String(10), nullable=False, server_default='en'))
    op.create_index('idx_documents_type', 'documents', ['document_type'])
    op.create_index('idx_documents_language', 'documents', ['language_code'])

    # 2. Add document_type and language_code to document_versions
    op.add_column('document_versions', sa.Column('document_type', sa.String(50), nullable=False, server_default='REGULATION'))
    op.add_column('document_versions', sa.Column('language_code', sa.String(10), nullable=False, server_default='en'))
    op.create_index('idx_doc_versions_type', 'document_versions', ['document_type'])
    op.create_index('idx_doc_versions_language', 'document_versions', ['language_code'])

    # 3. Create composite filter indexes for ultra-fast pre-filtering
    op.create_index(
        'idx_documents_filtering',
        'documents',
        ['status', 'academic_year_id', 'department_id', 'document_type', 'language_code'],
    )
    op.create_index(
        'idx_doc_versions_filtering',
        'document_versions',
        ['document_id', 'status', 'document_type', 'language_code', 'valid_from', 'valid_until'],
    )

    # 4. Populate search_vector on existing document_chunks
    op.execute("""
        UPDATE document_chunks
        SET search_vector = to_tsvector('english', coalesce(content, '')) || to_tsvector('simple', coalesce(content, ''))
        WHERE search_vector IS NULL;
    """)

    # 5. Create automatic trigger to maintain search_vector on chunk INSERT or UPDATE
    op.execute("""
        CREATE OR REPLACE FUNCTION document_chunks_search_vector_trigger() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english', coalesce(NEW.content, '')) || to_tsvector('simple', coalesce(NEW.content, ''));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS trg_chunks_search_vector ON document_chunks;
        CREATE TRIGGER trg_chunks_search_vector BEFORE INSERT OR UPDATE
        ON document_chunks FOR EACH ROW EXECUTE PROCEDURE document_chunks_search_vector_trigger();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_chunks_search_vector ON document_chunks;")
    op.execute("DROP FUNCTION IF EXISTS document_chunks_search_vector_trigger();")
    op.drop_index('idx_doc_versions_filtering', table_name='document_versions')
    op.drop_index('idx_documents_filtering', table_name='documents')
    op.drop_index('idx_doc_versions_language', table_name='document_versions')
    op.drop_index('idx_doc_versions_type', table_name='document_versions')
    op.drop_column('document_versions', 'language_code')
    op.drop_column('document_versions', 'document_type')
    op.drop_index('idx_documents_language', table_name='documents')
    op.drop_index('idx_documents_type', table_name='documents')
    op.drop_column('documents', 'language_code')
    op.drop_column('documents', 'document_type')
