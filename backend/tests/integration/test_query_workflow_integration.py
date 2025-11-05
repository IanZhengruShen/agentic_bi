"""
Integration tests for complete query workflow.

Tests the end-to-end workflow:
1. User authenticates
2. Selects database
3. Submits natural language query
4. Analysis Agent processes query
5. Visualization Agent generates chart
6. Results returned with SQL, data, chart, insights
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime

from app.main import app
from app.models.user import User


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def authenticated_user():
    """Mock authenticated user."""
    user = MagicMock(spec=User)
    user.id = "test-user-123"
    user.email = "analyst@example.com"
    user.full_name = "Test Analyst"
    user.company_id = "test-company-123"
    user.role = "analyst"
    user.is_active = True
    return user


@pytest.fixture
def mock_auth(authenticated_user):
    """Mock authentication dependency."""
    return patch('app.api.deps.get_current_user', return_value=authenticated_user)


@pytest.fixture
def mock_opa():
    """Mock OPA authorization."""
    return patch('app.api.workflows.opa_client.check_permission_or_raise', return_value=None)


class TestCompleteQueryWorkflow:
    """Tests for complete query workflow from query to visualization."""

    def test_successful_query_with_visualization(self, client, mock_auth, mock_opa):
        """Test successful query execution with automatic visualization."""

        mock_workflow_result = {
            "workflow_id": "wf-12345",
            "conversation_id": "conv-12345",
            "workflow_status": "completed",
            "workflow_stage": "completed",
            "query_success": True,
            "generated_sql": "SELECT region, SUM(sales) as total_sales FROM sales GROUP BY region",
            "sql_confidence": 0.95,
            "query_data": [
                {"region": "North", "total_sales": 125000},
                {"region": "South", "total_sales": 98000},
                {"region": "East", "total_sales": 156000},
                {"region": "West", "total_sales": 142000}
            ],
            "analysis_results": {
                "total_rows": 4,
                "descriptive_stats": {
                    "total_sales": {"mean": 130250, "std": 23145}
                }
            },
            "should_visualize": True,
            "visualization_id": "viz-12345",
            "chart_type": "bar",
            "plotly_figure": {
                "data": [{
                    "type": "bar",
                    "x": ["North", "South", "East", "West"],
                    "y": [125000, 98000, 156000, 142000],
                    "name": "Total Sales"
                }],
                "layout": {
                    "title": "Sales by Region",
                    "xaxis": {"title": "Region"},
                    "yaxis": {"title": "Total Sales"}
                }
            },
            "insights": [
                "Total sales across all regions: $521,000",
                "Highest performing region is East with $156,000 in sales",
                "South region shows 23% lower sales compared to average"
            ],
            "recommendations": [
                "Consider investigating factors contributing to East region's success",
                "Develop action plan to improve South region performance"
            ],
            "warnings": [],
            "errors": [],
            "agents_executed": ["analysis", "visualization"],
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "execution_time_ms": 2845
        }

        with mock_auth, mock_opa, \
             patch('app.api.workflows.create_unified_orchestrator') as mock_create_orchestrator:

            # Setup mock orchestrator
            mock_orchestrator = MagicMock()
            mock_orchestrator.execute = AsyncMock(return_value=mock_workflow_result)
            mock_create_orchestrator.return_value = mock_orchestrator

            # Execute query
            response = client.post(
                "/workflows/execute",
                json={
                    "query": "Show me sales by region",
                    "database": "sales_db",
                    "conversation_id": "conv-12345",
                    "options": {
                        "auto_visualize": True
                    }
                },
                headers={"Authorization": "Bearer test-token"}
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()

            # Check metadata
            assert data["metadata"]["workflow_id"] == "wf-12345"
            assert data["metadata"]["workflow_status"] == "completed"
            assert data["metadata"]["execution_time_ms"] == 2845

            # Check analysis results
            assert data["analysis"] is not None
            assert data["analysis"]["sql"]["query"] == mock_workflow_result["generated_sql"]
            assert data["analysis"]["sql"]["confidence"] == 0.95
            assert len(data["analysis"]["data"]) == 4
            assert data["analysis"]["insights"] == mock_workflow_result["insights"]
            assert data["analysis"]["recommendations"] == mock_workflow_result["recommendations"]

            # Check visualization
            assert data["visualization"] is not None
            assert data["visualization"]["chart_type"] == "bar"
            assert data["visualization"]["plotly_figure"] is not None
            assert len(data["visualization"]["plotly_figure"]["data"]) == 1

    def test_query_without_visualization(self, client, mock_auth, mock_opa):
        """Test query execution without visualization (data only)."""

        mock_workflow_result = {
            "workflow_id": "wf-67890",
            "workflow_status": "completed",
            "workflow_stage": "completed",
            "query_success": True,
            "generated_sql": "SELECT * FROM users LIMIT 10",
            "sql_confidence": 0.92,
            "query_data": [
                {"id": 1, "name": "Alice", "email": "alice@example.com"},
                {"id": 2, "name": "Bob", "email": "bob@example.com"}
            ],
            "should_visualize": False,  # No visualization needed
            "visualization_id": None,
            "chart_type": None,
            "plotly_figure": None,
            "insights": ["Retrieved 2 user records"],
            "recommendations": [],
            "warnings": [],
            "errors": [],
            "agents_executed": ["analysis"],
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "execution_time_ms": 1250
        }

        with mock_auth, mock_opa, \
             patch('app.api.workflows.create_unified_orchestrator') as mock_create_orchestrator:

            mock_orchestrator = MagicMock()
            mock_orchestrator.execute = AsyncMock(return_value=mock_workflow_result)
            mock_create_orchestrator.return_value = mock_orchestrator

            response = client.post(
                "/workflows/execute",
                json={
                    "query": "Show me the first 10 users",
                    "database": "users_db",
                    "options": {
                        "auto_visualize": False
                    }
                },
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["analysis"] is not None
            assert data["visualization"] is None  # No visualization
            assert len(data["analysis"]["data"]) == 2

    def test_query_with_sql_error(self, client, mock_auth, mock_opa):
        """Test query execution with SQL generation error."""

        mock_workflow_result = {
            "workflow_id": "wf-error-123",
            "workflow_status": "failed",
            "workflow_stage": "analysis",
            "query_success": False,
            "generated_sql": None,
            "sql_confidence": 0.0,
            "query_data": [],
            "should_visualize": False,
            "visualization_id": None,
            "chart_type": None,
            "plotly_figure": None,
            "insights": [],
            "recommendations": [],
            "warnings": [],
            "errors": [
                "Unable to generate SQL: Table 'non_existent_table' not found in schema"
            ],
            "agents_executed": ["analysis"],
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "execution_time_ms": 890
        }

        with mock_auth, mock_opa, \
             patch('app.api.workflows.create_unified_orchestrator') as mock_create_orchestrator:

            mock_orchestrator = MagicMock()
            mock_orchestrator.execute = AsyncMock(return_value=mock_workflow_result)
            mock_create_orchestrator.return_value = mock_orchestrator

            response = client.post(
                "/workflows/execute",
                json={
                    "query": "Show data from non_existent_table",
                    "database": "test_db"
                },
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 200  # Returns 200 but with error details
            data = response.json()
            assert data["metadata"]["workflow_status"] == "failed"
            assert len(data["analysis"]["errors"]) > 0
            assert "non_existent_table" in data["analysis"]["errors"][0]

    def test_query_with_partial_success(self, client, mock_auth, mock_opa):
        """Test query with analysis success but visualization failure."""

        mock_workflow_result = {
            "workflow_id": "wf-partial-123",
            "workflow_status": "partial_success",
            "workflow_stage": "completed",
            "query_success": True,
            "generated_sql": "SELECT * FROM sales",
            "sql_confidence": 0.90,
            "query_data": [{"sale_id": 1, "amount": 100}],
            "should_visualize": True,
            "visualization_id": None,
            "chart_type": None,
            "plotly_figure": None,
            "insights": ["Retrieved sales data"],
            "recommendations": [],
            "warnings": ["Visualization failed: Insufficient data for chart generation"],
            "errors": [],
            "agents_executed": ["analysis", "visualization"],
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "execution_time_ms": 2100
        }

        with mock_auth, mock_opa, \
             patch('app.api.workflows.create_unified_orchestrator') as mock_create_orchestrator:

            mock_orchestrator = MagicMock()
            mock_orchestrator.execute = AsyncMock(return_value=mock_workflow_result)
            mock_create_orchestrator.return_value = mock_orchestrator

            response = client.post(
                "/workflows/execute",
                json={
                    "query": "Visualize sales data",
                    "database": "sales_db",
                    "options": {"auto_visualize": True}
                },
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["metadata"]["workflow_status"] == "partial_success"
            assert data["analysis"] is not None
            assert len(data["analysis"]["warnings"]) > 0

    def test_query_with_conversation_context(self, client, mock_auth, mock_opa):
        """Test query with conversation context (follow-up question)."""

        mock_workflow_result = {
            "workflow_id": "wf-followup-123",
            "conversation_id": "conv-abc",
            "workflow_status": "completed",
            "workflow_stage": "completed",
            "query_success": True,
            "generated_sql": "SELECT region, SUM(sales) as total_sales FROM sales WHERE region = 'North' GROUP BY region",
            "sql_confidence": 0.93,
            "query_data": [{"region": "North", "total_sales": 125000}],
            "should_visualize": False,
            "insights": ["North region total sales: $125,000"],
            "recommendations": [],
            "warnings": [],
            "errors": [],
            "agents_executed": ["analysis"],
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "execution_time_ms": 1580
        }

        with mock_auth, mock_opa, \
             patch('app.api.workflows.create_unified_orchestrator') as mock_create_orchestrator:

            mock_orchestrator = MagicMock()
            mock_orchestrator.execute = AsyncMock(return_value=mock_workflow_result)
            mock_create_orchestrator.return_value = mock_orchestrator

            # Follow-up question (assumes previous context about regions)
            response = client.post(
                "/workflows/execute",
                json={
                    "query": "What about just the North region?",
                    "database": "sales_db",
                    "conversation_id": "conv-abc"  # Same conversation
                },
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["metadata"]["conversation_id"] == "conv-abc"
            assert "North" in data["analysis"]["data"][0]["region"]

    def test_query_validation_error(self, client, mock_auth, mock_opa):
        """Test query with validation error (missing required fields)."""

        with mock_auth, mock_opa:
            response = client.post(
                "/workflows/execute",
                json={
                    "query": "Show sales",
                    # Missing "database" field
                },
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 422  # Validation error

    def test_query_authorization_error(self, client, mock_auth):
        """Test query with authorization error (no permission)."""

        with mock_auth, \
             patch('app.api.workflows.opa_client.check_permission_or_raise',
                   side_effect=Exception("Permission denied: Cannot query database 'restricted_db'")):

            response = client.post(
                "/workflows/execute",
                json={
                    "query": "Show data",
                    "database": "restricted_db"
                },
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 403

    def test_query_with_analysis_tools(self, client, mock_auth, mock_opa):
        """Test query that triggers analysis tools (correlation, trend analysis)."""

        mock_workflow_result = {
            "workflow_id": "wf-tools-123",
            "workflow_status": "completed",
            "workflow_stage": "completed",
            "query_success": True,
            "generated_sql": "SELECT date, sales, marketing_spend FROM sales_data",
            "sql_confidence": 0.91,
            "query_data": [
                {"date": "2024-01", "sales": 100000, "marketing_spend": 15000},
                {"date": "2024-02", "sales": 120000, "marketing_spend": 18000}
            ],
            "analysis_results": {
                "correlation": {
                    "sales_marketing_correlation": 0.89,
                    "p_value": 0.002
                },
                "trend_analysis": {
                    "trend": "increasing",
                    "slope": 10000,
                    "confidence": 0.85
                }
            },
            "should_visualize": True,
            "chart_type": "line",
            "plotly_figure": {"data": [], "layout": {}},
            "insights": [
                "Strong positive correlation (0.89) between sales and marketing spend",
                "Sales show increasing trend with average monthly growth of $10,000"
            ],
            "recommendations": [
                "Continue current marketing investment strategy",
                "Consider increasing marketing budget for Q2"
            ],
            "warnings": [],
            "errors": [],
            "agents_executed": ["analysis", "visualization"],
            "tools_used": ["correlation_analysis", "trend_analysis"],
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "execution_time_ms": 3200
        }

        with mock_auth, mock_opa, \
             patch('app.api.workflows.create_unified_orchestrator') as mock_create_orchestrator:

            mock_orchestrator = MagicMock()
            mock_orchestrator.execute = AsyncMock(return_value=mock_workflow_result)
            mock_create_orchestrator.return_value = mock_orchestrator

            response = client.post(
                "/workflows/execute",
                json={
                    "query": "Analyze the correlation between sales and marketing spend, and show trends",
                    "database": "sales_db",
                    "options": {"auto_visualize": True}
                },
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "correlation" in str(data["analysis"]["insights"])
            assert "trend" in str(data["analysis"]["insights"])
