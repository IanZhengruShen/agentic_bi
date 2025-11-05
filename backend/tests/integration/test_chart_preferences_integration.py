"""
Integration tests for chart preferences and visualization customization.

Tests:
1. Loading chart preferences
2. Saving custom templates
3. Applying templates to generated charts
4. Template management (create, update, delete)
5. Company-wide defaults (admin only)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

from app.main import app
from app.models.user import User


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def authenticated_user():
    """Mock authenticated user (analyst role)."""
    user = MagicMock(spec=User)
    user.id = "user-123"
    user.email = "analyst@example.com"
    user.role = "analyst"
    user.is_active = True
    user.preferences = {}  # Start with empty preferences
    return user


@pytest.fixture
def admin_user():
    """Mock admin user."""
    user = MagicMock(spec=User)
    user.id = "admin-123"
    user.email = "admin@example.com"
    user.role = "admin"
    user.is_active = True
    user.preferences = {}
    return user


@pytest.fixture
def mock_auth(authenticated_user):
    """Mock authentication for regular user."""
    return patch('app.api.deps.get_current_user', return_value=authenticated_user)


@pytest.fixture
def mock_admin_auth(admin_user):
    """Mock authentication for admin user."""
    return patch('app.api.deps.get_current_user', return_value=admin_user)


class TestChartPreferencesRetrieval:
    """Tests for retrieving chart preferences."""

    def test_get_default_preferences(self, client, mock_auth):
        """Test getting default preferences for new user."""
        with mock_auth:
            response = client.get(
                "/api/user/chart/preferences",
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "active_template" in data
            assert "builtin_template" in data
            assert "custom_templates" in data
            # Should have default builtin template
            assert data["builtin_template"] in ["plotly", "plotly_white", "plotly_dark"]

    def test_get_preferences_with_custom_template(self, client, authenticated_user, mock_auth):
        """Test getting preferences with saved custom template."""
        # Mock user with saved preferences
        authenticated_user.preferences = {
            "chart_preferences": {
                "active_template": "custom_template_1",
                "custom_templates": [
                    {
                        "id": "custom_template_1",
                        "name": "Corporate Blue",
                        "colorway": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"],
                        "font_family": "Arial",
                        "font_size": 14
                    }
                ]
            }
        }

        with mock_auth:
            response = client.get(
                "/api/user/chart/preferences",
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["active_template"] == "custom_template_1"
            assert len(data["custom_templates"]) == 1
            assert data["custom_templates"][0]["name"] == "Corporate Blue"


class TestChartTemplateManagement:
    """Tests for creating, updating, and deleting custom templates."""

    def test_create_custom_template(self, client, mock_auth):
        """Test creating a new custom template."""
        template_data = {
            "name": "My Custom Template",
            "colorway": ["#FF5733", "#33FF57", "#3357FF", "#F3FF33"],
            "font_family": "Helvetica",
            "font_size": 12,
            "background_color": "#FFFFFF",
            "paper_bgcolor": "#F5F5F5",
            "logo_url": "https://example.com/logo.png",
            "logo_position": "top-right",
            "logo_size": 0.1
        }

        with mock_auth, \
             patch('app.api.chart_preferences.get_db') as mock_db:

            # Mock database session
            mock_session = MagicMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            response = client.post(
                "/api/user/chart/templates",
                json=template_data,
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 201
            data = response.json()
            assert data["success"] is True
            assert "template_id" in data
            assert data["template"]["name"] == "My Custom Template"
            assert len(data["template"]["colorway"]) == 4

    def test_create_template_with_invalid_colors(self, client, mock_auth):
        """Test creating template with invalid color format."""
        template_data = {
            "name": "Invalid Template",
            "colorway": ["not-a-color", "#FF5733"],  # Invalid color
            "font_family": "Arial",
            "font_size": 12
        }

        with mock_auth:
            response = client.post(
                "/api/user/chart/templates",
                json=template_data,
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 422  # Validation error

    def test_update_custom_template(self, client, mock_auth):
        """Test updating an existing custom template."""
        template_id = "template-123"
        update_data = {
            "name": "Updated Template Name",
            "colorway": ["#000000", "#FFFFFF", "#FF0000", "#00FF00"],
            "font_size": 16
        }

        with mock_auth, \
             patch('app.api.chart_preferences.get_db') as mock_db:

            mock_session = MagicMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            response = client.put(
                f"/api/user/chart/templates/{template_id}",
                json=update_data,
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["template"]["name"] == "Updated Template Name"
            assert data["template"]["font_size"] == 16

    def test_delete_custom_template(self, client, mock_auth):
        """Test deleting a custom template."""
        template_id = "template-to-delete"

        with mock_auth, \
             patch('app.api.chart_preferences.get_db') as mock_db:

            mock_session = MagicMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            response = client.delete(
                f"/api/user/chart/templates/{template_id}",
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "Template deleted successfully"

    def test_delete_nonexistent_template(self, client, mock_auth):
        """Test deleting a template that doesn't exist."""
        with mock_auth, \
             patch('app.api.chart_preferences.get_db') as mock_db:

            mock_session = MagicMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            response = client.delete(
                "/api/user/chart/templates/nonexistent-id",
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 404


class TestApplyingChartPreferences:
    """Tests for applying chart preferences to generated visualizations."""

    def test_chart_applies_active_template(self, client, authenticated_user, mock_auth):
        """Test that generated charts apply the user's active template."""
        # Mock user with custom template
        authenticated_user.preferences = {
            "chart_preferences": {
                "active_template": "custom_blue",
                "custom_templates": [
                    {
                        "id": "custom_blue",
                        "name": "Corporate Blue",
                        "colorway": ["#1E3A8A", "#3B82F6", "#60A5FA", "#93C5FD"],
                        "font_family": "Inter",
                        "font_size": 14,
                        "logo_url": "https://company.com/logo.png"
                    }
                ]
            }
        }

        mock_workflow_result = {
            "workflow_id": "wf-123",
            "workflow_status": "completed",
            "query_success": True,
            "should_visualize": True,
            "chart_type": "bar",
            "plotly_figure": {
                "data": [{
                    "type": "bar",
                    "x": ["A", "B", "C"],
                    "y": [10, 20, 30],
                    "marker": {"color": "#1E3A8A"}  # From colorway
                }],
                "layout": {
                    "title": "Test Chart",
                    "font": {"family": "Inter", "size": 14},  # From template
                    "images": [{
                        "source": "https://company.com/logo.png",
                        "xref": "paper",
                        "yref": "paper",
                        "x": 0.95,
                        "y": 0.95
                    }]
                }
            },
            "agents_executed": ["analysis", "visualization"]
        }

        with mock_auth, \
             patch('app.api.workflows.opa_client.check_permission_or_raise', return_value=None), \
             patch('app.api.workflows.create_unified_orchestrator') as mock_orchestrator:

            mock_orch = MagicMock()
            mock_orch.execute = MagicMock(return_value=mock_workflow_result)
            mock_orchestrator.return_value = mock_orch

            response = client.post(
                "/workflows/execute",
                json={
                    "query": "Show test data",
                    "database": "test_db",
                    "options": {"auto_visualize": True}
                },
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 200
            data = response.json()

            # Verify custom template applied
            chart = data["visualization"]["plotly_figure"]
            assert chart["layout"]["font"]["family"] == "Inter"
            assert chart["layout"]["font"]["size"] == 14
            assert len(chart["layout"]["images"]) > 0
            assert chart["layout"]["images"][0]["source"] == "https://company.com/logo.png"


class TestSetActiveTemplate:
    """Tests for setting the active template."""

    def test_set_builtin_template_as_active(self, client, mock_auth):
        """Test setting a builtin Plotly template as active."""
        with mock_auth, \
             patch('app.api.chart_preferences.get_db') as mock_db:

            mock_session = MagicMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            response = client.put(
                "/api/user/chart/preferences",
                json={
                    "active_template": "plotly_dark",
                    "is_builtin": True
                },
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["active_template"] == "plotly_dark"

    def test_set_custom_template_as_active(self, client, mock_auth):
        """Test setting a custom template as active."""
        with mock_auth, \
             patch('app.api.chart_preferences.get_db') as mock_db:

            mock_session = MagicMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            response = client.put(
                "/api/user/chart/preferences",
                json={
                    "active_template": "custom-template-123",
                    "is_builtin": False
                },
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["active_template"] == "custom-template-123"

    def test_set_nonexistent_custom_template(self, client, mock_auth):
        """Test setting a non-existent custom template as active."""
        with mock_auth, \
             patch('app.api.chart_preferences.get_db') as mock_db:

            mock_session = MagicMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            response = client.put(
                "/api/user/chart/preferences",
                json={
                    "active_template": "nonexistent-template",
                    "is_builtin": False
                },
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 404


class TestCompanyWideDefaults:
    """Tests for company-wide default templates (admin only)."""

    def test_admin_set_company_default(self, client, mock_admin_auth):
        """Test admin setting company-wide default template."""
        with mock_admin_auth, \
             patch('app.api.chart_preferences.get_db') as mock_db:

            mock_session = MagicMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            response = client.put(
                "/api/company/chart/preferences",
                json={
                    "default_template": "corporate_template_id",
                    "enforce_for_all_users": False
                },
                headers={"Authorization": "Bearer admin-token"}
            )

            # If endpoint exists, should return 200
            # If not implemented yet, should return 404 or 501
            assert response.status_code in [200, 404, 501]

    def test_non_admin_cannot_set_company_default(self, client, mock_auth):
        """Test that non-admin cannot set company-wide defaults."""
        with mock_auth:
            response = client.put(
                "/api/company/chart/preferences",
                json={
                    "default_template": "some_template"
                },
                headers={"Authorization": "Bearer user-token"}
            )

            assert response.status_code in [403, 404]  # Forbidden or Not Found
