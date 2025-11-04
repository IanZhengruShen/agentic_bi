"""create HITL tables

Revision ID: 49427bdaa598
Revises: a1b2c3d4e5f6
Create Date: 2025-11-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision: str = '49427bdaa598'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create HITL tables for human-in-the-loop interventions."""

    # Create hitl_requests table
    op.create_table(
        'hitl_requests',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('request_id', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('workflow_id', sa.String(255), nullable=False, index=True),
        sa.Column('conversation_id', sa.String(255), nullable=True),
        sa.Column('intervention_type', sa.String(100), nullable=False, index=True),
        sa.Column('context', JSON, nullable=False, server_default='{}'),
        sa.Column('options', JSON, nullable=False, server_default='[]'),
        sa.Column('requester_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('status', sa.String(50), nullable=False, default='pending', index=True),
        sa.Column('requested_at', sa.DateTime, nullable=False),
        sa.Column('timeout_seconds', sa.Integer, nullable=False, default=300),
        sa.Column('timeout_at', sa.DateTime, nullable=False),
        sa.Column('responded_at', sa.DateTime, nullable=True),
        sa.Column('response_time_ms', sa.Integer, nullable=True),
        sa.Column('required', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )

    # Create hitl_responses table
    op.create_table(
        'hitl_responses',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('request_id', UUID(as_uuid=True), sa.ForeignKey('hitl_requests.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('data', JSON, nullable=True),
        sa.Column('feedback', sa.Text, nullable=True),
        sa.Column('modified_sql', sa.Text, nullable=True),
        sa.Column('responder_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('responder_name', sa.String(255), nullable=True),
        sa.Column('responder_email', sa.String(255), nullable=True),
        sa.Column('response_time_ms', sa.Integer, nullable=True),
        sa.Column('responded_at', sa.DateTime, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )

    # Create indexes for common queries
    op.create_index('idx_hitl_workflow_status', 'hitl_requests', ['workflow_id', 'status'])
    op.create_index('idx_hitl_company_type', 'hitl_requests', ['company_id', 'intervention_type'])
    op.create_index('idx_hitl_timeout_at', 'hitl_requests', ['timeout_at'])


def downgrade() -> None:
    """Drop HITL tables."""
    op.drop_index('idx_hitl_responses_request', table_name='hitl_responses')
    op.drop_index('idx_hitl_requests_company_status', table_name='hitl_requests')
    op.drop_index('idx_hitl_requests_workflow_status', table_name='hitl_requests')
    op.drop_table('hitl_responses')
    op.drop_table('hitl_requests')
