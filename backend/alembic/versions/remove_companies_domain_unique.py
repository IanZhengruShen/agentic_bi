"""remove unique constraint from companies.domain

Revision ID: remove_companies_domain_unique
Revises: add_notification_prefs
Create Date: 2025-01-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'remove_companies_domain_unique'
down_revision: Union[str, None] = 'add_notification_prefs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove unique constraint from companies.domain column.

    Multiple users can have the same email domain (e.g., @example.com)
    and they don't necessarily belong to the same company.
    """
    # Drop the unique constraint on domain
    op.drop_constraint('companies_domain_key', 'companies', type_='unique')


def downgrade() -> None:
    """Restore unique constraint (may fail if duplicate domains exist)."""
    op.create_unique_constraint('companies_domain_key', 'companies', ['domain'])
