"""add notification preferences to users

Revision ID: add_notification_prefs
Revises:
Create Date: 2025-11-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_notification_prefs'
down_revision = None  # Will be set by alembic
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add notification_preferences column to users table
    op.add_column('users', sa.Column(
        'notification_preferences',
        postgresql.JSON(astext_type=sa.Text()),
        nullable=True,
        server_default=sa.text("'{\"channels\": [\"slack\", \"email\"], \"slack_enabled\": true, \"email_enabled\": true, \"intervention_types\": null}'::json")
    ))


def downgrade() -> None:
    # Remove notification_preferences column
    op.drop_column('users', 'notification_preferences')
