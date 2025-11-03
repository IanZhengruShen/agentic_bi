"""
API tests for unified workflow endpoints.

Tests the REST API endpoints for executing unified workflows.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_current_user():
    """Mock authenticated user."""
    user = MagicMock()
    user.id = "user-123"
    user.company_id = "company-123"
    user.role = "analyst"
    user.is_active = True
    return user


class TestWorkflowExecuteEndpoint:
    """Tests for POST /workflows/execute endpoint."""

    def test_execute_workflow_success(self, client, mock_current_user):
        """Test successful workflow execution."""

        # Mock successful workflow result
        mock_workflow_result = {
            "workflow_id": "workflow-123",
            "workflow_status": "completed",
            "workflow_stage": "completed",
            "query_success": True,
            "generated_sql": "SELECT * FROM sales",
            "query_data": [{"region": "North", "sales": 1000}],
            "analysis_results": {"total": 1000},
            "visualization_id": "viz-123",
            "chart_type": "bar",
            "plotly_figure": {"data": [], "layout": {}},
            "should_visualize": True,
            "insights": ["Sales data retrieved"],
            "recommendations": [],
            "errors": [],
            "warnings": [],
            "agents_executed": ["analysis", "visualization"],
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "execution_time_ms": 1500,
        }

        with patch('app.api.workflows.get_current_active_user', return_value=mock_current_user), \
             patch('app.api.workflows.opa_client.check_permission_or_raise', return_value=None), \
             patch('app.api.workflows.create_unified_orchestrator') as mock_create_orchestrator:

            # Setup mock orchestrator
            mock_orchestrator = MagicMock()
            mock_orchestrator.execute = AsyncMock(return_value=mock_workflow_result)
            mock_create_orchestrator.return_value = mock_orchestrator

            # Make request
            response = client.post(
                "/workflows/execute",
                json={
                    "query": "Show sales by region",
                    "database": "test_db",
                    "options": {
                        "auto_visualize": True,
                    }
                },
                headers={"Authorization": "Bearer fake-token"}
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["metadata"]["workflow_id"] == "workflow-123"
            assert data["metadata"]["workflow_status"] == "completed"
            assert data["analysis"] is not None
            assert data["visualization"] is not None

    def test_execute_workflow_permission_denied(self, client, mock_current_user):
        """Test workflow execution with insufficient permissions."""

        with patch('app.api.workflows.get_current_active_user', return_value=mock_current_user), \
             patch('app.api.workflows.opa_client.check_permission_or_raise',
                   side_effect=Exception("Permission denied")):

            response = client.post(
                "/workflows/execute",
                json={
                    "query": "Show sales",
                    "database": "test_db",
                },
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code == 403

    def test_execute_workflow_validation_error(self, client, mock_current_user):
        """Test workflow execution with invalid request."""

        with patch('app.api.workflows.get_current_active_user', return_value=mock_current_user):

            # Missing required field
            response = client.post(
                "/workflows/execute",
                json={
                    "query": "Show sales",
                    # Missing "database" field
                },
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code == 422  # Validation error


class TestWorkflowStatusEndpoint:
    """Tests for GET /workflows/{workflow_id}/status endpoint."""

    def test_get_workflow_status(self, client, mock_current_user):
        """Test getting workflow status."""

        with patch('app.api.workflows.get_current_active_user', return_value=mock_current_user):

            response = client.get(
                "/workflows/workflow-123/status",
                headers={"Authorization": "Bearer fake-token"}
            )

            # Currently returns placeholder
            assert response.status_code == 200
            data = response.json()
            assert data["workflow_id"] == "workflow-123"
            assert data["status"] == "unknown"  # Placeholder


class TestWorkflowResultsEndpoint:
    """Tests for GET /workflows/{workflow_id} endpoint."""

    def test_get_workflow_results_not_implemented(self, client, mock_current_user):
        """Test getting workflow results (not yet implemented)."""

        with patch('app.api.workflows.get_current_active_user', return_value=mock_current_user):

            response = client.get(
                "/workflows/workflow-123",
                headers={"Authorization": "Bearer fake-token"}
            )

            # Currently not implemented
            assert response.status_code == 501


class TestWorkflowCancelEndpoint:
    """Tests for DELETE /workflows/{workflow_id} endpoint."""

    def test_cancel_workflow_not_implemented(self, client, mock_current_user):
        """Test canceling workflow (not yet implemented)."""

        with patch('app.api.workflows.get_current_active_user', return_value=mock_current_user):

            response = client.delete(
                "/workflows/workflow-123",
                headers={"Authorization": "Bearer fake-token"}
            )

            # Currently not implemented
            assert response.status_code == 501
