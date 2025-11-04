"""fix hitl request_id column types to be consistent

Revision ID: fix_hitl_request_id_types
Revises: fix_hitl_tables_schema
Create Date: 2025-11-04 21:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fix_hitl_request_id_types'
down_revision: Union[str, None] = 'fix_hitl_tables_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Fix request_id columns to be consistent VARCHAR(255) in both tables.

    The issue: request_id should be VARCHAR in both hitl_requests and hitl_responses,
    but the database might have UUID type from a previous migration.
    """

    # Use raw SQL to handle type conversion safely
    conn = op.get_bind()

    # Check current types
    result = conn.execute(sa.text("""
        SELECT
            table_name,
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_name IN ('hitl_requests', 'hitl_responses')
        AND column_name = 'request_id'
        ORDER BY table_name
    """))

    current_types = {row[0]: row[2] for row in result}

    print(f"Current request_id types: {current_types}")

    # Fix hitl_requests.request_id if it's UUID
    if current_types.get('hitl_requests') == 'uuid':
        print("Converting hitl_requests.request_id from UUID to VARCHAR(255)")
        conn.execute(sa.text("""
            ALTER TABLE hitl_requests
            ALTER COLUMN request_id TYPE VARCHAR(255) USING request_id::text
        """))

    # Fix hitl_responses.request_id if it's UUID
    if current_types.get('hitl_responses') == 'uuid':
        print("Converting hitl_responses.request_id from UUID to VARCHAR(255)")

        # Need to drop foreign key first
        conn.execute(sa.text("""
            ALTER TABLE hitl_responses
            DROP CONSTRAINT IF EXISTS hitl_responses_request_id_fkey
        """))

        # Convert to VARCHAR
        conn.execute(sa.text("""
            ALTER TABLE hitl_responses
            ALTER COLUMN request_id TYPE VARCHAR(255) USING request_id::text
        """))

        # Re-add foreign key
        conn.execute(sa.text("""
            ALTER TABLE hitl_responses
            ADD CONSTRAINT hitl_responses_request_id_fkey
            FOREIGN KEY (request_id)
            REFERENCES hitl_requests(request_id)
            ON DELETE CASCADE
        """))

    print("Migration complete: request_id columns are now VARCHAR(255) in both tables")


def downgrade() -> None:
    """Reverse the changes (not implemented as this is a fix migration)."""
    pass
