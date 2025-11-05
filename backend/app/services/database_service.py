"""
Database service for fetching and filtering databases.

Integrates MindsDB for database discovery and OPA for authorization.
"""
import logging
from typing import List, Dict, Any, Optional

from app.services.mindsdb_service import MindsDBService
from app.services.opa_client import OPAClient

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for managing database access."""

    def __init__(self, mindsdb_service: MindsDBService, opa_client: OPAClient):
        """
        Initialize database service.

        Args:
            mindsdb_service: MindsDB service instance
            opa_client: OPA client instance
        """
        self.mindsdb = mindsdb_service
        self.opa = opa_client

    async def get_accessible_databases(
        self,
        user_id: str,
        company_id: Optional[str],
        role: str
    ) -> List[Dict[str, Any]]:
        """
        Get list of databases accessible to user.

        Fetches all databases from MindsDB and filters by user permissions via OPA.

        Args:
            user_id: User UUID
            company_id: Company UUID (optional)
            role: User role (admin, analyst, viewer, user)

        Returns:
            List of database dicts with format:
            [
                {
                    "name": "sales_db",
                    "display_name": "Sales Database",
                    "engine": "postgres",
                    "description": "Sales data warehouse"
                },
                ...
            ]

        Raises:
            Exception: If there's an error fetching databases
        """
        try:
            # 1. Fetch all databases from MindsDB
            all_databases = await self.mindsdb.get_databases()
            logger.info(f"Retrieved {len(all_databases)} databases from MindsDB")
            logger.info(f"Checking access for user_id={user_id}, role={role}, company_id={company_id}")

            # 2. Filter by user permissions via OPA
            accessible_databases = []

            for db in all_databases:
                db_name = db.get("name")
                if not db_name:
                    continue

                # Check permission via OPA
                has_access = await self.opa.check_permission(
                    user_id=user_id,
                    company_id=company_id,
                    role=role,
                    action="read",
                    resource_type="database",
                    resource_data={"database_name": db_name}
                )

                logger.info(f"OPA check: database={db_name}, role={role}, has_access={has_access}")

                if has_access:
                    # Format database info
                    accessible_databases.append({
                        "name": db_name,
                        "display_name": db.get("display_name") or self._format_display_name(db_name),
                        "engine": db.get("engine") or "unknown",
                        "description": db.get("description") or ""
                    })

            logger.info(
                f"User {user_id} (role={role}) has access to {len(accessible_databases)}/{len(all_databases)} databases: {[db['name'] for db in accessible_databases]}"
            )

            return accessible_databases

        except Exception as e:
            logger.error(f"Error fetching accessible databases: {e}", exc_info=True)
            # Fail gracefully - return empty list rather than raising
            # This ensures the UI doesn't break if MindsDB or OPA is down
            return []

    def _format_display_name(self, db_name: str) -> str:
        """
        Format database name for display.

        Converts snake_case to Title Case.

        Args:
            db_name: Database name (e.g., "sales_db")

        Returns:
            Formatted display name (e.g., "Sales Db")

        Example:
            >>> self._format_display_name("sales_db")
            "Sales Db"
            >>> self._format_display_name("customer_analytics")
            "Customer Analytics"
        """
        return db_name.replace("_", " ").title()
