"""
Unit tests for workflow coordination nodes.

Tests the adapter nodes that coordinate between the unified workflow
and individual agent subgraphs.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.workflows.coordination_nodes import (
    run_analysis_adapter_node,
    decide_visualization_node,
    run_visualization_adapter_node,
    aggregate_results_node,
    should_visualize_router,
)
from app.workflows.unified_state import UnifiedWorkflowState


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    client = MagicMock()
    client.generate_text = AsyncMock()
    return client


@pytest.fixture
def base_unified_state():
    """Create base unified workflow state for testing."""
    return {
        "workflow_id": "test-workflow-123",
        "user_query": "Show sales by region",
        "database": "test_db",
        "user_id": "user-123",
        "company_id": "company-123",
        "options": {},
        "workflow_status": "pending",
        "workflow_stage": "init",
        "current_agent": None,
        "analysis_session_id": None,
        "schema": None,
        "generated_sql": None,
        "sql_confidence": None,
        "query_success": False,
        "query_data": None,
        "analysis_results": None,
        "enhanced_analysis": None,
        "should_visualize": False,
        "visualization_reasoning": None,
        "skip_visualization_reason": None,
        "visualization_id": None,
        "recommended_chart_type": None,
        "chart_type": None,
        "plotly_figure": None,
        "chart_insights": [],
        "insights": [],
        "recommendations": [],
        "errors": [],
        "warnings": [],
        "partial_success": False,
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "execution_time_ms": None,
        "agents_executed": [],
    }


class TestRunAnalysisAdapterNode:
    """Tests for run_analysis_adapter_node."""

    @pytest.mark.asyncio
    async def test_successful_analysis(self, mock_llm_client, base_unified_state):
        """Test successful analysis execution."""
        # Mock AnalysisAgent workflow result
        mock_analysis_result = {
            "workflow_status": "completed",
            "query_success": True,
            "generated_sql": "SELECT * FROM sales",
            "confidence": 0.95,
            "query_data": [{"region": "North", "sales": 1000}],
            "analysis_results": {"total_sales": 1000},
            "enhanced_analysis": {"trend": "increasing"},
            "insights": ["Sales are trending up"],
            "recommendations": ["Focus on North region"],
            "warnings": [],
            "errors": [],
        }

        with patch('app.workflows.coordination_nodes.AnalysisAgentLangGraph') as MockAgent:
            # Setup mock
            mock_agent_instance = MagicMock()
            mock_agent_instance.workflow.ainvoke = AsyncMock(return_value=mock_analysis_result)
            MockAgent.return_value = mock_agent_instance

            # Execute node
            result = await run_analysis_adapter_node(
                base_unified_state,
                llm_client=mock_llm_client,
            )

            # Verify results
            assert result["workflow_status"] == "analyzed"
            assert result["current_agent"] == "analysis"
            assert result["query_success"] is True
            assert result["generated_sql"] == "SELECT * FROM sales"
            assert result["sql_confidence"] == 0.95
            assert len(result["query_data"]) == 1
            assert "analysis" in result["agents_executed"]

    @pytest.mark.asyncio
    async def test_analysis_failure(self, mock_llm_client, base_unified_state):
        """Test analysis failure handling."""
        with patch('app.workflows.coordination_nodes.AnalysisAgentLangGraph') as MockAgent:
            # Setup mock to raise exception
            mock_agent_instance = MagicMock()
            mock_agent_instance.workflow.ainvoke = AsyncMock(
                side_effect=Exception("Database connection failed")
            )
            MockAgent.return_value = mock_agent_instance

            # Execute node
            result = await run_analysis_adapter_node(
                base_unified_state,
                llm_client=mock_llm_client,
            )

            # Verify error handling
            assert result["workflow_status"] == "failed"
            assert len(result["errors"]) > 0
            assert "Database connection failed" in result["errors"][0]


class TestDecideVisualizationNode:
    """Tests for decide_visualization_node."""

    @pytest.mark.asyncio
    async def test_skip_if_query_failed(self, mock_llm_client, base_unified_state):
        """Test skipping visualization if query failed."""
        state = base_unified_state.copy()
        state["query_success"] = False

        result = await decide_visualization_node(state, mock_llm_client)

        assert result["should_visualize"] is False
        assert "failed" in result["skip_visualization_reason"].lower()

    @pytest.mark.asyncio
    async def test_skip_if_no_data(self, mock_llm_client, base_unified_state):
        """Test skipping visualization if no data."""
        state = base_unified_state.copy()
        state["query_success"] = True
        state["query_data"] = []

        result = await decide_visualization_node(state, mock_llm_client)

        assert result["should_visualize"] is False
        assert "no data" in result["skip_visualization_reason"].lower()

    @pytest.mark.asyncio
    async def test_skip_if_auto_visualize_disabled(self, mock_llm_client, base_unified_state):
        """Test skipping visualization if disabled by user."""
        state = base_unified_state.copy()
        state["query_success"] = True
        state["query_data"] = [{"region": "North", "sales": 1000}]
        state["options"] = {"auto_visualize": False}

        result = await decide_visualization_node(state, mock_llm_client)

        assert result["should_visualize"] is False
        assert "disabled" in result["skip_visualization_reason"].lower()

    @pytest.mark.asyncio
    async def test_llm_decides_to_visualize(self, mock_llm_client, base_unified_state):
        """Test LLM decision to visualize."""
        state = base_unified_state.copy()
        state["query_success"] = True
        state["query_data"] = [
            {"region": "North", "sales": 1000},
            {"region": "South", "sales": 1500},
        ]
        state["analysis_results"] = {"summary": "Sales vary by region"}

        # Mock LLM response
        mock_llm_client.generate_text.return_value = '''
        {
            "should_visualize": true,
            "reasoning": "Chart would help compare regions",
            "suggested_chart_type": "bar"
        }
        '''

        result = await decide_visualization_node(state, mock_llm_client)

        assert result["should_visualize"] is True
        assert "reasoning" in result["visualization_reasoning"]
        assert result.get("recommended_chart_type") == "bar"

    @pytest.mark.asyncio
    async def test_llm_failure_defaults_to_visualize(self, mock_llm_client, base_unified_state):
        """Test that LLM failure defaults to visualizing."""
        state = base_unified_state.copy()
        state["query_success"] = True
        state["query_data"] = [{"region": "North", "sales": 1000}]

        # Mock LLM failure
        mock_llm_client.generate_text.side_effect = Exception("LLM timeout")

        result = await decide_visualization_node(state, mock_llm_client)

        # Should default to True (bias toward visualizing)
        assert result["should_visualize"] is True
        assert len(result.get("warnings", [])) > 0


class TestRunVisualizationAdapterNode:
    """Tests for run_visualization_adapter_node."""

    @pytest.mark.asyncio
    async def test_successful_visualization(self, mock_llm_client, base_unified_state):
        """Test successful visualization creation."""
        state = base_unified_state.copy()
        state["query_data"] = [{"region": "North", "sales": 1000}]
        state["analysis_results"] = {"total_sales": 1000}
        state["analysis_session_id"] = "session-123"

        # Mock VisualizationAgent workflow result
        mock_viz_result = {
            "workflow_status": "completed",
            "chart_type": "bar",
            "plotly_figure": {"data": [], "layout": {}},
            "chart_insights": ["North has highest sales"],
            "warnings": [],
            "errors": [],
        }

        with patch('app.workflows.coordination_nodes.VisualizationAgent') as MockAgent:
            # Setup mock
            mock_agent_instance = MagicMock()
            mock_agent_instance.workflow.ainvoke = AsyncMock(return_value=mock_viz_result)
            MockAgent.return_value = mock_agent_instance

            # Execute node
            result = await run_visualization_adapter_node(
                state,
                llm_client=mock_llm_client,
            )

            # Verify results
            assert result["workflow_status"] == "visualized"
            assert result["current_agent"] == "visualization"
            assert result["chart_type"] == "bar"
            assert result["plotly_figure"] is not None
            assert "visualization" in result["agents_executed"]

    @pytest.mark.asyncio
    async def test_visualization_failure_partial_success(self, mock_llm_client, base_unified_state):
        """Test visualization failure returns partial success."""
        state = base_unified_state.copy()
        state["query_data"] = [{"region": "North", "sales": 1000}]

        with patch('app.workflows.coordination_nodes.VisualizationAgent') as MockAgent:
            # Setup mock to raise exception
            mock_agent_instance = MagicMock()
            mock_agent_instance.workflow.ainvoke = AsyncMock(
                side_effect=Exception("Chart generation failed")
            )
            MockAgent.return_value = mock_agent_instance

            # Execute node
            result = await run_visualization_adapter_node(
                state,
                llm_client=mock_llm_client,
            )

            # Verify partial success (not fatal)
            assert result["partial_success"] is True
            assert len(result["warnings"]) > 0
            assert "Chart generation failed" in result["warnings"][0]


class TestAggregateResultsNode:
    """Tests for aggregate_results_node."""

    @pytest.mark.asyncio
    async def test_successful_aggregation(self, base_unified_state):
        """Test successful result aggregation."""
        state = base_unified_state.copy()
        state["insights"] = ["Insight from analysis"]
        state["chart_insights"] = ["Insight from chart"]
        state["agents_executed"] = ["analysis", "visualization"]

        result = await aggregate_results_node(state)

        assert result["workflow_status"] == "completed"
        assert result["workflow_stage"] == "completed"
        assert result["execution_time_ms"] > 0
        assert result["completed_at"] is not None
        # Insights should be combined
        assert len(result["insights"]) == 2

    @pytest.mark.asyncio
    async def test_aggregation_with_errors(self, base_unified_state):
        """Test aggregation with errors results in failed status."""
        state = base_unified_state.copy()
        state["errors"] = ["Analysis failed"]
        state["partial_success"] = False

        result = await aggregate_results_node(state)

        assert result["workflow_status"] == "failed"

    @pytest.mark.asyncio
    async def test_aggregation_partial_success(self, base_unified_state):
        """Test aggregation with partial success."""
        state = base_unified_state.copy()
        state["partial_success"] = True
        state["warnings"] = ["Visualization failed"]

        result = await aggregate_results_node(state)

        assert result["workflow_status"] == "partial_success"


class TestShouldVisualizeRouter:
    """Tests for should_visualize_router."""

    def test_route_to_visualize(self, base_unified_state):
        """Test routing to visualization."""
        state = base_unified_state.copy()
        state["should_visualize"] = True

        route = should_visualize_router(state)

        assert route == "visualize"

    def test_route_to_skip(self, base_unified_state):
        """Test routing to skip visualization."""
        state = base_unified_state.copy()
        state["should_visualize"] = False

        route = should_visualize_router(state)

        assert route == "skip"
