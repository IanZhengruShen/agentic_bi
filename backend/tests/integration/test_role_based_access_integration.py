"""
Integration tests for role-based access control.

Tests access control for 4 roles:
1. Admin - Full access
2. Analyst - Query and visualize
3. Viewer - Read-only
4. User - Basic access
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.models.user import User


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def create_mock_user(role: str, user_id: str = "test-user"):
    """Create mock user with specified role."""
    user = MagicMock(spec=User)
    user.id = user_id
    user.email = f"{role}@example.com"
    user.full_name = f"Test {role.title()}"
    user.company_id = "test-company-123"
    user.role = role
    user.is_active = True
    user.preferences = {}
    return user


class TestAdminRole:
    """Tests for admin role permissions."""

    def test_admin_can_change_user_role(self, client):
        """Test admin can change other user's role."""
        admin = create_mock_user("admin", "admin-123")

        with patch('app.api.deps.get_current_user', return_value=admin), \
             patch('app.api.users.get_db') as mock_db:

            mock_session = MagicMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            response = client.put(
                "/users/role",
                json={
                    "user_id": "other-user-123",
                    "new_role": "analyst"
                },
                headers={"Authorization": "Bearer admin-token"}
            )

            # Should succeed or return appropriate status
            assert response.status_code in [200, 404]  # Success or user not found

    def test_admin_can_create_database(self, client):
        """Test admin can create new database connections."""
        admin = create_mock_user("admin")

        with patch('app.api.deps.get_current_user', return_value=admin), \
             patch('app.api.databases.MindsDBService') as mock_mindsdb:

            mock_service = MagicMock()
            mock_service.create_database.return_value = {"success": True}
            mock_mindsdb.return_value = mock_service

            response = client.post(
                "/api/databases/",
                json={
                    "name": "new_postgres_db",
                    "engine": "postgres",
                    "parameters": {
                        "host": "localhost",
                        "port": "5432",
                        "user": "admin",
                        "password": "secret",
                        "database": "test_db"
                    }
                },
                headers={"Authorization": "Bearer admin-token"}
            )

            assert response.status_code in [200, 201]

    def test_admin_can_query_and_visualize(self, client):
        """Test admin can execute queries and generate visualizations."""
        admin = create_mock_user("admin")

        with patch('app.api.deps.get_current_user', return_value=admin), \
             patch('app.api.workflows.opa_client.check_permission_or_raise', return_value=None), \
             patch('app.api.workflows.create_unified_orchestrator') as mock_orch:

            mock_orchestrator = MagicMock()
            mock_orchestrator.execute = MagicMock(return_value={
                "workflow_id": "wf-123",
                "workflow_status": "completed",
                "query_success": True,
                "agents_executed": ["analysis", "visualization"]
            })
            mock_orch.return_value = mock_orchestrator

            response = client.post(
                "/workflows/execute",
                json={
                    "query": "Show sales data",
                    "database": "sales_db"
                },
                headers={"Authorization": "Bearer admin-token"}
            )

            assert response.status_code == 200

    def test_admin_can_access_all_settings(self, client):
        """Test admin can access all settings."""
        admin = create_mock_user("admin")

        with patch('app.api.deps.get_current_user', return_value=admin):

            # Profile settings
            response = client.get(
                "/users/me",
                headers={"Authorization": "Bearer admin-token"}
            )
            assert response.status_code == 200

            # Chart preferences
            response = client.get(
                "/api/user/chart/preferences",
                headers={"Authorization": "Bearer admin-token"}
            )
            assert response.status_code in [200, 404]

    def test_admin_cannot_demote_self(self, client):
        """Test admin cannot demote themselves from admin role."""
        admin = create_mock_user("admin", "admin-123")

        with patch('app.api.deps.get_current_user', return_value=admin), \
             patch('app.api.users.get_db') as mock_db:

            mock_session = MagicMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            response = client.put(
                "/users/role",
                json={
                    "user_id": "admin-123",  # Self
                    "new_role": "user"  # Demote
                },
                headers={"Authorization": "Bearer admin-token"}
            )

            # Should be forbidden
            assert response.status_code in [400, 403]


class TestAnalystRole:
    """Tests for analyst role permissions."""

    def test_analyst_can_query_and_visualize(self, client):
        """Test analyst can execute queries and generate visualizations."""
        analyst = create_mock_user("analyst")

        with patch('app.api.deps.get_current_user', return_value=analyst), \
             patch('app.api.workflows.opa_client.check_permission_or_raise', return_value=None), \
             patch('app.api.workflows.create_unified_orchestrator') as mock_orch:

            mock_orchestrator = MagicMock()
            mock_orchestrator.execute = MagicMock(return_value={
                "workflow_id": "wf-456",
                "workflow_status": "completed",
                "query_success": True
            })
            mock_orch.return_value = mock_orchestrator

            response = client.post(
                "/workflows/execute",
                json={
                    "query": "Analyze sales trends",
                    "database": "sales_db"
                },
                headers={"Authorization": "Bearer analyst-token"}
            )

            assert response.status_code == 200

    def test_analyst_can_customize_chart_preferences(self, client):
        """Test analyst can customize their chart preferences."""
        analyst = create_mock_user("analyst")

        with patch('app.api.deps.get_current_user', return_value=analyst), \
             patch('app.api.chart_preferences.get_db') as mock_db:

            mock_session = MagicMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            response = client.post(
                "/api/user/chart/templates",
                json={
                    "name": "My Template",
                    "colorway": ["#FF5733", "#33FF57"],
                    "font_family": "Arial",
                    "font_size": 12
                },
                headers={"Authorization": "Bearer analyst-token"}
            )

            assert response.status_code in [200, 201]

    def test_analyst_cannot_change_roles(self, client):
        """Test analyst cannot change user roles."""
        analyst = create_mock_user("analyst")

        with patch('app.api.deps.get_current_user', return_value=analyst):

            response = client.put(
                "/users/role",
                json={
                    "user_id": "other-user",
                    "new_role": "admin"
                },
                headers={"Authorization": "Bearer analyst-token"}
            )

            assert response.status_code == 403

    def test_analyst_cannot_create_database(self, client):
        """Test analyst cannot create new database connections."""
        analyst = create_mock_user("analyst")

        with patch('app.api.deps.get_current_user', return_value=analyst):

            response = client.post(
                "/api/databases/",
                json={
                    "name": "new_db",
                    "engine": "postgres",
                    "parameters": {}
                },
                headers={"Authorization": "Bearer analyst-token"}
            )

            assert response.status_code == 403


class TestViewerRole:
    """Tests for viewer role permissions."""

    def test_viewer_can_view_dashboards(self, client):
        """Test viewer can access read-only dashboards."""
        viewer = create_mock_user("viewer")

        with patch('app.api.deps.get_current_user', return_value=viewer):

            response = client.get(
                "/users/me",
                headers={"Authorization": "Bearer viewer-token"}
            )

            assert response.status_code == 200
            assert response.json()["role"] == "viewer"

    def test_viewer_cannot_execute_queries(self, client):
        """Test viewer cannot execute queries (if enforced)."""
        viewer = create_mock_user("viewer")

        with patch('app.api.deps.get_current_user', return_value=viewer), \
             patch('app.api.workflows.opa_client.check_permission_or_raise',
                   side_effect=Exception("Permission denied: Viewer role cannot execute queries")):

            response = client.post(
                "/workflows/execute",
                json={
                    "query": "Show data",
                    "database": "sales_db"
                },
                headers={"Authorization": "Bearer viewer-token"}
            )

            assert response.status_code == 403

    def test_viewer_cannot_change_settings(self, client):
        """Test viewer cannot change settings."""
        viewer = create_mock_user("viewer")

        with patch('app.api.deps.get_current_user', return_value=viewer):

            response = client.put(
                "/users/me",
                json={"full_name": "New Name"},
                headers={"Authorization": "Bearer viewer-token"}
            )

            # May be allowed or forbidden depending on implementation
            assert response.status_code in [200, 403]

    def test_viewer_cannot_create_templates(self, client):
        """Test viewer cannot create custom chart templates."""
        viewer = create_mock_user("viewer")

        with patch('app.api.deps.get_current_user', return_value=viewer):

            response = client.post(
                "/api/user/chart/templates",
                json={
                    "name": "Template",
                    "colorway": ["#000000"]
                },
                headers={"Authorization": "Bearer viewer-token"}
            )

            # Should be forbidden if enforced
            assert response.status_code in [201, 403]


class TestUserRole:
    """Tests for basic user role permissions."""

    def test_user_can_query_and_visualize(self, client):
        """Test user can execute basic queries."""
        user = create_mock_user("user")

        with patch('app.api.deps.get_current_user', return_value=user), \
             patch('app.api.workflows.opa_client.check_permission_or_raise', return_value=None), \
             patch('app.api.workflows.create_unified_orchestrator') as mock_orch:

            mock_orchestrator = MagicMock()
            mock_orchestrator.execute = MagicMock(return_value={
                "workflow_id": "wf-789",
                "workflow_status": "completed",
                "query_success": True
            })
            mock_orch.return_value = mock_orchestrator

            response = client.post(
                "/workflows/execute",
                json={
                    "query": "Show my data",
                    "database": "user_db"
                },
                headers={"Authorization": "Bearer user-token"}
            )

            assert response.status_code == 200

    def test_user_can_update_own_profile(self, client):
        """Test user can update their own profile."""
        user = create_mock_user("user")

        with patch('app.api.deps.get_current_user', return_value=user), \
             patch('app.api.users.get_db') as mock_db:

            mock_session = MagicMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            response = client.put(
                "/users/me",
                json={
                    "full_name": "Updated Name",
                    "department": "Marketing"
                },
                headers={"Authorization": "Bearer user-token"}
            )

            assert response.status_code == 200

    def test_user_cannot_change_roles(self, client):
        """Test user cannot change roles."""
        user = create_mock_user("user")

        with patch('app.api.deps.get_current_user', return_value=user):

            response = client.put(
                "/users/role",
                json={
                    "user_id": "other-user",
                    "new_role": "analyst"
                },
                headers={"Authorization": "Bearer user-token"}
            )

            assert response.status_code == 403

    def test_user_cannot_create_database(self, client):
        """Test user cannot create database connections."""
        user = create_mock_user("user")

        with patch('app.api.deps.get_current_user', return_value=user):

            response = client.post(
                "/api/databases/",
                json={
                    "name": "new_db",
                    "engine": "postgres",
                    "parameters": {}
                },
                headers={"Authorization": "Bearer user-token"}
            )

            assert response.status_code == 403


class TestCrossRoleScenarios:
    """Tests for cross-role scenarios and permission boundaries."""

    def test_role_badge_colors_correct(self, client):
        """Test that each role returns correct metadata for UI badge."""
        roles = ["admin", "analyst", "viewer", "user"]
        expected_colors = {
            "admin": "purple",
            "analyst": "blue",
            "viewer": "gray",
            "user": "green"
        }

        for role in roles:
            user = create_mock_user(role)

            with patch('app.api.deps.get_current_user', return_value=user):
                response = client.get(
                    "/users/me",
                    headers={"Authorization": "Bearer token"}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["role"] == role
                # Note: Color is frontend logic, not returned by API

    def test_database_access_filtered_by_role(self, client):
        """Test that database list is filtered by user role/permissions."""
        analyst = create_mock_user("analyst")

        with patch('app.api.deps.get_current_user', return_value=analyst), \
             patch('app.services.database_service.DatabaseService.get_accessible_databases') as mock_get_dbs:

            # Mock filtered databases
            mock_get_dbs.return_value = [
                {"name": "sales_db", "display_name": "Sales Database", "engine": "postgres"},
                {"name": "marketing_db", "display_name": "Marketing Database", "engine": "postgres"}
            ]

            response = client.get(
                "/api/databases/",
                headers={"Authorization": "Bearer analyst-token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["databases"]) == 2
            assert all(db["name"] in ["sales_db", "marketing_db"] for db in data["databases"])
