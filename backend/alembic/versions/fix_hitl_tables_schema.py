"""fix HITL tables schema - add missing columns

Revision ID: fix_hitl_tables_schema
Revises: remove_companies_domain_unique
Create Date: 2025-11-04 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'fix_hitl_tables_schema'
down_revision: Union[str, None] = 'remove_companies_domain_unique'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns to HITL tables."""

    # Check and add missing columns to hitl_requests
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)

    # Get existing columns
    existing_columns = [col['name'] for col in inspector.get_columns('hitl_requests')]

    # Add request_id if missing
    if 'request_id' not in existing_columns:
        op.add_column('hitl_requests',
            sa.Column('request_id', sa.String(255), unique=True, nullable=True, index=True))

    # Add timeout_at if missing (was named expires_at before)
    if 'timeout_at' not in existing_columns:
        if 'expires_at' in existing_columns:
            op.alter_column('hitl_requests', 'expires_at', new_column_name='timeout_at')
        else:
            op.add_column('hitl_requests',
                sa.Column('timeout_at', sa.DateTime, nullable=True))

    # Add responded_at if missing
    if 'responded_at' not in existing_columns:
        op.add_column('hitl_requests',
            sa.Column('responded_at', sa.DateTime, nullable=True))

    # Add response_time_ms if missing
    if 'response_time_ms' not in existing_columns:
        op.add_column('hitl_requests',
            sa.Column('response_time_ms', sa.Integer, nullable=True))

    # Add required if missing
    if 'required' not in existing_columns:
        op.add_column('hitl_requests',
            sa.Column('required', sa.Boolean, nullable=False, server_default='true'))

    # Fix foreign key columns to use UUID type
    if 'requester_user_id' in existing_columns:
        # Drop and recreate with correct type
        op.drop_column('hitl_requests', 'requester_user_id')
        op.add_column('hitl_requests',
            sa.Column('requester_user_id', UUID(as_uuid=True),
                     sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))

    if 'company_id' in existing_columns:
        # Drop and recreate with correct type
        op.drop_column('hitl_requests', 'company_id')
        op.add_column('hitl_requests',
            sa.Column('company_id', UUID(as_uuid=True),
                     sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=True, index=True))

    # Fix hitl_responses responder_user_id
    responses_columns = [col['name'] for col in inspector.get_columns('hitl_responses')]
    if 'responder_user_id' in responses_columns:
        op.drop_column('hitl_responses', 'responder_user_id')
        op.add_column('hitl_responses',
            sa.Column('responder_user_id', UUID(as_uuid=True),
                     sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))


def downgrade() -> None:
    """Reverse the changes (not fully implemented as this is a fix migration)."""
    pass
