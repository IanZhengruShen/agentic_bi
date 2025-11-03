"""create_auth_tables

Revision ID: dce4b39f5a36
Revises:
Create Date: 2025-11-03 13:43:47.653948

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision: str = 'dce4b39f5a36'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create companies table
    op.create_table(
        'companies',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('domain', sa.String(255), unique=True),
        sa.Column('logo_url', sa.String(500)),
        sa.Column('settings', JSON, nullable=False, server_default='{}'),
        sa.Column('style_config', JSON, server_default='{}'),
        sa.Column('subscription_tier', sa.String(50), server_default='free'),
        sa.Column('subscription_expires_at', sa.DateTime),
        sa.Column('user_limit', sa.Integer, server_default='10'),
        sa.Column('query_limit_monthly', sa.Integer, server_default='1000'),
        sa.Column('storage_limit_gb', sa.Integer, server_default='10'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_companies_domain', 'companies', ['domain'])
    op.create_index('idx_companies_active', 'companies', ['is_active'])

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('avatar_url', sa.String(500)),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id', ondelete='CASCADE')),
        sa.Column('department', sa.String(100)),
        sa.Column('role', sa.String(50), server_default='user'),
        sa.Column('permissions', JSON, server_default='{}'),
        sa.Column('preferences', JSON, server_default='{}'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('is_verified', sa.Boolean, server_default='false'),
        sa.Column('last_login_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_company', 'users', ['company_id'])
    op.create_index('idx_users_active', 'users', ['is_active'])

    # Create refresh_tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(255), unique=True, nullable=False),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('revoked_at', sa.DateTime),
        sa.Column('is_active', sa.Boolean, server_default='true'),
    )
    op.create_index('idx_refresh_tokens_user', 'refresh_tokens', ['user_id'])
    op.create_index('idx_refresh_tokens_hash', 'refresh_tokens', ['token_hash'])
    op.create_index('idx_refresh_tokens_active', 'refresh_tokens', ['is_active', 'expires_at'])


def downgrade() -> None:
    op.drop_table('refresh_tokens')
    op.drop_table('users')
    op.drop_table('companies')
