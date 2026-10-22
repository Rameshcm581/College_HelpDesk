"""support_ticketing_and_otp

Revision ID: 0005_support_ticketing
Revises: 0004_admin_dashboard
Create Date: 2026-10-22 17:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0005_support_ticketing'
down_revision: Union[str, None] = '0004_admin_dashboard'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add ASSIGNED and WAITING_FOR_USER to ticket_status_enum in autocommit block
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE ticket_status_enum ADD VALUE IF NOT EXISTS 'ASSIGNED'")
        op.execute("ALTER TYPE ticket_status_enum ADD VALUE IF NOT EXISTS 'WAITING_FOR_USER'")

    # 2. Add new columns to tickets table
    op.add_column('tickets', sa.Column('subject', sa.String(255), nullable=True))
    op.add_column('tickets', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('tickets', sa.Column('sla_due_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tickets', sa.Column('resolved_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))
    op.add_column('tickets', sa.Column('resolution_notes', sa.Text(), nullable=True))

    op.create_index('idx_tickets_sla_due', 'tickets', ['sla_due_at'])
    op.create_index('idx_tickets_category', 'tickets', ['category'])

    # Backfill subject and description for any existing tickets
    op.execute("""
        UPDATE tickets 
        SET subject = COALESCE(subject, category || ' Support Request - ' || ticket_number),
            description = COALESCE(description, 'Support inquiry regarding ' || category)
        WHERE subject IS NULL;
    """)

    # 3. Create ticket_status_history table
    op.create_table(
        'ticket_status_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('ticket_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('from_status', sa.String(50), nullable=False),
        sa.Column('to_status', sa.String(50), nullable=False),
        sa.Column('changed_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_ticket_history_ticket', 'ticket_status_history', ['ticket_id', 'created_at'])

    # 4. Create ticket_otps table for secure visitor OTP tracking
    op.create_table(
        'ticket_otps',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('ticket_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('otp_hash', sa.String(64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default=sa.text('3')),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_ticket_otps_ticket_email', 'ticket_otps', ['ticket_id', 'email'])
    op.create_index('idx_ticket_otps_expiry', 'ticket_otps', ['expires_at', 'is_used'])

    # 5. Seed missing departments to support full routing
    op.execute("""
        INSERT INTO departments (id, code, name, contact_email, is_active)
        VALUES 
        (
            gen_random_uuid(),
            'FIN',
            'Accounts & Finance Office',
            'accounts@college.edu',
            true
        ),
        (
            gen_random_uuid(),
            'SCH',
            'Student Welfare & Scholarships Cell',
            'scholarships@college.edu',
            true
        ),
        (
            gen_random_uuid(),
            'PLC',
            'Career Guidance & Placement Cell',
            'placements@college.edu',
            true
        ),
        (
            gen_random_uuid(),
            'GEN',
            'General Administration',
            'helpdesk@college.edu',
            true
        )
        ON CONFLICT (code) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_table('ticket_otps')
    op.drop_table('ticket_status_history')
    op.drop_index('idx_tickets_category', table_name='tickets')
    op.drop_index('idx_tickets_sla_due', table_name='tickets')
    op.drop_column('tickets', 'resolution_notes')
    op.drop_column('tickets', 'resolved_by_id')
    op.drop_column('tickets', 'sla_due_at')
    op.drop_column('tickets', 'description')
    op.drop_column('tickets', 'subject')
