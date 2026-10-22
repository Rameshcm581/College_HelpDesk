"""admin_dashboard_and_roles

Revision ID: 0004_admin_dashboard
Revises: 0003_metadata_search
Create Date: 2026-10-22 17:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0004_admin_dashboard'
down_revision: Union[str, None] = '0003_metadata_search'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new role values to user_role_enum in an autocommit block
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE user_role_enum ADD VALUE IF NOT EXISTS 'ADMIN'")
        op.execute("ALTER TYPE user_role_enum ADD VALUE IF NOT EXISTS 'DEPARTMENT_STAFF'")
        op.execute("ALTER TYPE user_role_enum ADD VALUE IF NOT EXISTS 'VIEWER'")

    # 2. Create system_settings table for institutional configuration
    op.create_table(
        'system_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('key', sa.String(100), nullable=False, unique=True),
        sa.Column('value', postgresql.JSONB, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('updated_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_system_settings_key', 'system_settings', ['key'], unique=True)

    # 3. Insert baseline system configuration
    op.execute("""
        INSERT INTO system_settings (key, value, description)
        VALUES 
        (
            'college_branding',
            '{"college_name": "St. Jude College of Engineering & Technology", "short_name": "SJCET", "tagline": "Empowering Future Engineers & Innovators", "brand_color": "#1e40af", "theme": "system"}'::jsonb,
            'College naming, short name, tagline, and brand styling'
        ),
        (
            'welcome_messages',
            '{"en": "Welcome to the College AI Help Desk! How can I assist you today with admissions, fees, hostel, or examinations?", "ta": "செயின்ட் ஜூட் கல்லூரி AI உதவி மையத்திற்கு நல்வரவு! சேர்க்கை, கட்டணம், விடுதி அல்லது தேர்வுகள் குறித்து எவ்வாறு உதவலாம்?"}'::jsonb,
            'Bilingual greetings shown upon opening chatbot'
        ),
        (
            'supported_languages',
            '["en", "ta", "ta-Latn"]'::jsonb,
            'Active language locales permitted by institution'
        ),
        (
            'suggested_questions',
            '["What is the annual tuition fee for B.E. Computer Science?", "How much is the hostel caution deposit and is it refundable?", "What are the rules regarding exam attendance condonation?", "முதல் தலைமுறை பட்டதாரி கல்வி உதவித்தொகை எவ்வளவு?"]'::jsonb,
            'One-click starter prompt chips displayed in widget'
        ),
        (
            'approved_origins',
            '["http://localhost:5173", "http://localhost:5175", "http://127.0.0.1:5175", "https://college.edu"]'::jsonb,
            'Allowed host website domains for embedding widget iframe'
        )
        ON CONFLICT (key) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_index('idx_system_settings_key', table_name='system_settings')
    op.drop_table('system_settings')
