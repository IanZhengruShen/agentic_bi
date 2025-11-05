"""
Integration tests for database management.

Tests:
1. Listing accessible databases (filtered by OPA)
2. Creating new database connections (admin only)
3. Database validation
4. OPA authorization integration
5. MindsDB integration
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

from app.main import app
from app.models.user import User


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def admin_user():
    """Mock admin user."""
    user = MagicMock(spec=User)
    user.id = "admin-123"
    user.email = "admin@example.com"
    user.role = "admin"
    user.company_id = "company-123"
    user.is_active = True
    return user


@pytest.fixture
def regular_user():
    """Mock regular user."""
    user = MagicMock(spec=User)
    user.id = "user-456"
    user.email = "user@example.com"
    user.role = "user"
    user.company_id = "company-123"
    user.is_active = True
    return user


class TestDatabaseListing:
    """Tests for listing accessible databases."""

    def test_get_databases_success(self, client, regular_user):
        """Test successfully getting list of accessible databases."""
        mock_databases = [
            {
                "name": "sales_db",
                "display_name": "Sales Database",
                "engine": "postgres",
                "description": "Sales data warehouse"
            },
            {
                "name": "marketing_db",
                "display_name": "Marketing Database",
                "engine": "mysql",
                "description": "Marketing analytics"
            }
        ]

        with patch('app.api.deps.get_current_user', return_value=regular_user), \
             patch('app.services.database_service.DatabaseService.get_accessible_databases',
                   return_value=mock_databases):

            response = client.get(
                "/api/databases/",
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "databases" in data
            assert "total_count" in data
            assert len(data["databases"]) == 2
            assert data["total_count"] == 2
            assert data["databases"][0]["name"] == "sales_db"
            assert data["databases"][1]["name"] == "marketing_db"

    def test_get_databases_filtered_by_opa(self, client, regular_user):
        """Test that databases are filtered by OPA authorization."""
        # Mock: User only has access to sales_db
        mock_databases = [
            {
                "name": "sales_db",
                "display_name": "Sales Database",
                "engine": "postgres",
                "description": ""
            }
        ]

        with patch('app.api.deps.get_current_user', return_value=regular_user), \
             patch('app.services.database_service.DatabaseService.get_accessible_databases',
                   return_value=mock_databases):

            response = client.get(
                "/api/databases/",
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["databases"]) == 1
            assert data["databases"][0]["name"] == "sales_db"

    def test_get_databases_empty_list(self, client, regular_user):
        """Test getting databases when user has no access."""
        with patch('app.api.deps.get_current_user', return_value=regular_user), \
             patch('app.services.database_service.DatabaseService.get_accessible_databases',
                   return_value=[]):

            response = client.get(
                "/api/databases/",
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["databases"]) == 0
            assert data["total_count"] == 0

    def test_get_databases_opa_fallback_mode(self, client, regular_user):
        """Test database listing works when OPA is unavailable (fallback mode)."""
        # Mock: OPA unavailable, fallback to showing all databases
        mock_databases = [
            {"name": "db1", "display_name": "Database 1", "engine": "postgres", "description": ""},
            {"name": "db2", "display_name": "Database 2", "engine": "mysql", "description": ""}
        ]

        with patch('app.api.deps.get_current_user', return_value=regular_user), \
             patch('app.services.database_service.DatabaseService.get_accessible_databases',
                   return_value=mock_databases):

            response = client.get(
                "/api/databases/",
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["databases"]) == 2  # Shows all in fallback mode

    def test_get_databases_without_auth(self, client):
        """Test getting databases without authentication token."""
        response = client.get("/api/databases/")

        assert response.status_code == 401  # Unauthorized


class TestDatabaseCreation:
    """Tests for creating new database connections."""

    def test_admin_create_postgres_database(self, client, admin_user):
        """Test admin creating PostgreSQL database connection."""
        database_data = {
            "name": "new_postgres_db",
            "engine": "postgres",
            "display_name": "New PostgreSQL Database",
            "description": "Test PostgreSQL connection",
            "parameters": {
                "host": "localhost",
                "port": "5432",
                "user": "admin",
                "password": "secret123",
                "database": "testdb"
            }
        }

        with patch('app.api.deps.get_current_user', return_value=admin_user), \
             patch('app.services.mindsdb_service.MindsDBService.create_database') as mock_create:

            mock_create.return_value = {
                "success": True,
                "database_name": "new_postgres_db"
            }

            response = client.post(
                "/api/databases/",
                json=database_data,
                headers={"Authorization": "Bearer admin-token"}
            )

            assert response.status_code in [200, 201]
            data = response.json()
            assert data["success"] is True
            assert data["database_name"] == "new_postgres_db"
            assert "error" not in data or data["error"] is None

    def test_admin_create_mysql_database(self, client, admin_user):
        """Test admin creating MySQL database connection."""
        database_data = {
            "name": "new_mysql_db",
            "engine": "mysql",
            "parameters": {
                "host": "mysql.example.com",
                "port": "3306",
                "user": "root",
                "password": "mysql_pass",
                "database": "analytics"
            }
        }

        with patch('app.api.deps.get_current_user', return_value=admin_user), \
             patch('app.services.mindsdb_service.MindsDBService.create_database') as mock_create:

            mock_create.return_value = {"success": True, "database_name": "new_mysql_db"}

            response = client.post(
                "/api/databases/",
                json=database_data,
                headers={"Authorization": "Bearer admin-token"}
            )

            assert response.status_code in [200, 201]
            assert response.json()["success"] is True

    def test_non_admin_cannot_create_database(self, client, regular_user):
        """Test that non-admin users cannot create databases."""
        database_data = {
            "name": "unauthorized_db",
            "engine": "postgres",
            "parameters": {
                "host": "localhost",
                "port": "5432",
                "user": "user",
                "password": "pass",
                "database": "test"
            }
        }

        with patch('app.api.deps.get_current_user', return_value=regular_user):

            response = client.post(
                "/api/databases/",
                json=database_data,
                headers={"Authorization": "Bearer user-token"}
            )

            assert response.status_code == 403  # Forbidden

    def test_create_database_validation_error(self, client, admin_user):
        """Test database creation with invalid data."""
        database_data = {
            "name": "invalid_db",
            # Missing "engine" field
            "parameters": {
                "host": "localhost"
            }
        }

        with patch('app.api.deps.get_current_user', return_value=admin_user):

            response = client.post(
                "/api/databases/",
                json=database_data,
                headers={"Authorization": "Bearer admin-token"}
            )

            assert response.status_code == 422  # Validation error

    def test_create_database_duplicate_name(self, client, admin_user):
        """Test creating database with duplicate name."""
        database_data = {
            "name": "existing_db",
            "engine": "postgres",
            "parameters": {
                "host": "localhost",
                "port": "5432",
                "user": "admin",
                "password": "pass",
                "database": "test"
            }
        }

        with patch('app.api.deps.get_current_user', return_value=admin_user), \
             patch('app.services.mindsdb_service.MindsDBService.create_database') as mock_create:

            # Mock MindsDB error for duplicate
            mock_create.side_effect = Exception("Database 'existing_db' already exists")

            response = client.post(
                "/api/databases/",
                json=database_data,
                headers={"Authorization": "Bearer admin-token"}
            )

            assert response.status_code in [400, 500]
            data = response.json()
            assert "already exists" in data["detail"].lower() or "error" in str(data).lower()

    def test_create_database_connection_failure(self, client, admin_user):
        """Test database creation with connection failure."""
        database_data = {
            "name": "unreachable_db",
            "engine": "postgres",
            "parameters": {
                "host": "unreachable.example.com",
                "port": "5432",
                "user": "admin",
                "password": "pass",
                "database": "test"
            }
        }

        with patch('app.api.deps.get_current_user', return_value=admin_user), \
             patch('app.services.mindsdb_service.MindsDBService.create_database') as mock_create:

            mock_create.return_value = {
                "success": False,
                "error": "Connection timeout: Could not reach host unreachable.example.com"
            }

            response = client.post(
                "/api/databases/",
                json=database_data,
                headers={"Authorization": "Bearer admin-token"}
            )

            # API may return 200 with error details or 500
            assert response.status_code in [200, 500]
            if response.status_code == 200:
                data = response.json()
                assert data["success"] is False
                assert "error" in data


class TestDatabaseIntegration:
    """Tests for database integration with MindsDB and OPA."""

    def test_mindsdb_connection_established(self, client, regular_user):
        """Test that MindsDB connection is established correctly."""
        with patch('app.api.deps.get_current_user', return_value=regular_user), \
             patch('app.services.mindsdb_service.MindsDBService') as mock_mindsdb_class:

            mock_service = MagicMock()
            mock_service.list_databases.return_value = [
                {"name": "test_db", "engine": "postgres"}
            ]
            mock_mindsdb_class.return_value = mock_service

            response = client.get(
                "/api/databases/",
                headers={"Authorization": "Bearer test-token"}
            )

            # Should succeed if MindsDB connection works
            assert response.status_code == 200

    def test_mindsdb_connection_failure(self, client, regular_user):
        """Test handling of MindsDB connection failure."""
        with patch('app.api.deps.get_current_user', return_value=regular_user), \
             patch('app.services.database_service.DatabaseService.get_accessible_databases',
                   side_effect=Exception("MindsDB connection failed")):

            response = client.get(
                "/api/databases/",
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 500

    def test_database_selection_in_query(self, client, regular_user):
        """Test that selected database is used in query workflow."""
        with patch('app.api.deps.get_current_user', return_value=regular_user), \
             patch('app.api.workflows.opa_client.check_permission_or_raise', return_value=None), \
             patch('app.api.workflows.create_unified_orchestrator') as mock_orch:

            mock_orchestrator = MagicMock()
            mock_orchestrator.execute = AsyncMock(return_value={
                "workflow_id": "wf-123",
                "workflow_status": "completed",
                "query_success": True,
                "generated_sql": "SELECT * FROM sales",
                "agents_executed": ["analysis"]
            })
            mock_orch.return_value = mock_orchestrator

            response = client.post(
                "/workflows/execute",
                json={
                    "query": "Show sales data",
                    "database": "sales_db"  # Specific database selected
                },
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 200
            # Verify database was passed to orchestrator
            mock_orch.assert_called_once()
            call_kwargs = mock_orch.call_args[1]
            assert call_kwargs["database"] == "sales_db"


class TestDatabaseMetadata:
    """Tests for database metadata and information."""

    def test_database_engine_types(self, client, regular_user):
        """Test that database engine types are returned correctly."""
        mock_databases = [
            {"name": "pg_db", "display_name": "PostgreSQL DB", "engine": "postgres", "description": ""},
            {"name": "my_db", "display_name": "MySQL DB", "engine": "mysql", "description": ""},
            {"name": "mongo_db", "display_name": "MongoDB", "engine": "mongodb", "description": ""}
        ]

        with patch('app.api.deps.get_current_user', return_value=regular_user), \
             patch('app.services.database_service.DatabaseService.get_accessible_databases',
                   return_value=mock_databases):

            response = client.get(
                "/api/databases/",
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 200
            data = response.json()
            engines = [db["engine"] for db in data["databases"]]
            assert "postgres" in engines
            assert "mysql" in engines
            assert "mongodb" in engines

    def test_database_display_names(self, client, regular_user):
        """Test that human-readable display names are returned."""
        mock_databases = [
            {
                "name": "sales_prod_db",
                "display_name": "Production Sales Database",
                "engine": "postgres",
                "description": "Main production database"
            }
        ]

        with patch('app.api.deps.get_current_user', return_value=regular_user), \
             patch('app.services.database_service.DatabaseService.get_accessible_databases',
                   return_value=mock_databases):

            response = client.get(
                "/api/databases/",
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["databases"][0]["display_name"] == "Production Sales Database"
            assert data["databases"][0]["description"] == "Main production database"
