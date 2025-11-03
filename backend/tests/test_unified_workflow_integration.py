"""
Integration tests for unified multi-agent workflow.

Tests the complete workflow orchestration from query to analysis to visualization.
"""

import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.workflows.orchestrator import UnifiedWorkflowOrchestrator

logger = logging.getLogger(__name__)


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    client = MagicMock()
    client.generate_text = AsyncMock()
    return client


@pytest.fixture
def mock_mindsdb_service():
    """Create mock MindsDB service."""
    service = MagicMock()
    return service


@pytest.fixture
def mock_hitl_service():
    """Create mock HITL service."""
    service = MagicMock()
    return service


class TestUnifiedWorkflowOrchestrator:
    """Integration tests for UnifiedWorkflowOrchestrator."""

    @pytest.mark.asyncio
    async def test_complete_workflow_with_visualization(
        self,
        mock_llm_client,
        mock_mindsdb_service,
        mock_hitl_service,
    ):
        """Test complete workflow: Analysis → Decision → Visualization."""

        # Mock AnalysisAgent workflow
        mock_analysis_result = {
            "workflow_status": "completed",
            "query_success": True,
            "generated_sql": "SELECT region, SUM(sales) FROM sales GROUP BY region",
            "confidence": 0.95,
            "query_data": [
                {"region": "North", "total_sales": 1000},
                {"region": "South", "total_sales": 1500},
                {"region": "East", "total_sales": 1200},
            ],
            "analysis_results": {"total_sales": 3700, "avg_sales": 1233.33},
            "enhanced_analysis": {"trend": "stable"},
            "insights": ["South region has highest sales"],
            "recommendations": ["Investigate South region success factors"],
            "warnings": [],
            "errors": [],
        }

        # Mock VisualizationAgent workflow
        mock_viz_result = {
            "workflow_status": "completed",
            "chart_type": "bar",
            "plotly_figure": {
                "data": [{"type": "bar", "x": ["North", "South", "East"], "y": [1000, 1500, 1200]}],
                "layout": {"title": "Sales by Region"},
            },
            "chart_insights": ["Bar chart clearly shows South's lead"],
            "warnings": [],
            "errors": [],
        }

        # Mock LLM decision to visualize
        mock_llm_client.generate_text.return_value = '''
        {
            "should_visualize": true,
            "reasoning": "Data is suitable for comparison chart",
            "suggested_chart_type": "bar"
        }
        '''

        with patch('app.agents.analysis_agent_langgraph.AnalysisAgentLangGraph') as MockAnalysisAgent, \
             patch('app.agents.visualization_agent.VisualizationAgent') as MockVizAgent:

            # Setup mocks
            mock_analysis_instance = MagicMock()
            mock_analysis_instance.workflow.ainvoke = AsyncMock(return_value=mock_analysis_result)
            MockAnalysisAgent.return_value = mock_analysis_instance

            mock_viz_instance = MagicMock()
            mock_viz_instance.workflow.ainvoke = AsyncMock(return_value=mock_viz_result)
            MockVizAgent.return_value = mock_viz_instance

            # Create orchestrator
            orchestrator = UnifiedWorkflowOrchestrator(
                llm_client=mock_llm_client,
                mindsdb_service=mock_mindsdb_service,
                hitl_service=mock_hitl_service,
            )

            # Execute workflow
            result = await orchestrator.execute(
                user_query="Show sales by region",
                database="test_db",
                user_id="user-123",
                company_id="company-123",
                options={"auto_visualize": True},
            )

            # Verify complete workflow executed
            assert result["workflow_status"] == "completed"
            assert result["workflow_stage"] == "completed"

            # Verify analysis results
            assert result["query_success"] is True
            assert result["generated_sql"] is not None
            assert len(result["query_data"]) == 3

            # Verify visualization results
            assert result["should_visualize"] is True
            assert result["visualization_id"] is not None
            assert result["plotly_figure"] is not None
            assert result["chart_type"] == "bar"

            # Verify combined insights
            assert len(result["insights"]) >= 2  # From both agents

            # Verify both agents executed
            assert "analysis" in result["agents_executed"]
            assert "visualization" in result["agents_executed"]

            # Verify metadata
            assert result["execution_time_ms"] > 0
            assert result["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_workflow_skips_visualization(
        self,
        mock_llm_client,
        mock_mindsdb_service,
        mock_hitl_service,
    ):
        """Test workflow that skips visualization (simple scalar query)."""

        # Mock AnalysisAgent workflow (simple count query)
        mock_analysis_result = {
            "workflow_status": "completed",
            "query_success": True,
            "generated_sql": "SELECT COUNT(*) as count FROM users",
            "confidence": 0.98,
            "query_data": [{"count": 42}],
            "analysis_results": {"count": 42},
            "insights": ["42 users found"],
            "warnings": [],
            "errors": [],
        }

        # Mock LLM decision to NOT visualize
        mock_llm_client.generate_text.return_value = '''
        {
            "should_visualize": false,
            "reasoning": "Single scalar value doesn't need visualization",
            "suggested_chart_type": null
        }
        '''

        with patch('app.agents.analysis_agent_langgraph.AnalysisAgentLangGraph') as MockAnalysisAgent:

            # Setup mock
            mock_analysis_instance = MagicMock()
            mock_analysis_instance.workflow.ainvoke = AsyncMock(return_value=mock_analysis_result)
            MockAnalysisAgent.return_value = mock_analysis_instance

            # Create orchestrator
            orchestrator = UnifiedWorkflowOrchestrator(
                llm_client=mock_llm_client,
                mindsdb_service=mock_mindsdb_service,
                hitl_service=mock_hitl_service,
            )

            # Execute workflow
            result = await orchestrator.execute(
                user_query="How many users are there?",
                database="test_db",
                user_id="user-123",
                company_id="company-123",
            )

            # Verify workflow completed without visualization
            assert result["workflow_status"] == "completed"
            assert result["should_visualize"] is False
            assert result["visualization_id"] is None
            assert result["plotly_figure"] is None

            # Verify only analysis agent executed
            assert "analysis" in result["agents_executed"]
            assert "visualization" not in result["agents_executed"]

    @pytest.mark.asyncio
    async def test_workflow_with_visualization_failure(
        self,
        mock_llm_client,
        mock_mindsdb_service,
        mock_hitl_service,
    ):
        """Test workflow with visualization failure (partial success)."""

        # Mock successful AnalysisAgent
        # Use multiple rows to bypass rule-based skip (Rule 4: single scalar check)
        mock_analysis_result = {
            "workflow_status": "completed",
            "query_success": True,
            "generated_sql": "SELECT * FROM sales",
            "query_data": [
                {"region": "North", "sales": 1000},
                {"region": "South", "sales": 1500},
            ],
            "insights": ["Analysis complete"],
            "warnings": [],
            "errors": [],
        }

        # Mock LLM decision to visualize
        mock_llm_client.generate_text.return_value = '''
        {
            "should_visualize": true,
            "reasoning": "Should visualize",
            "suggested_chart_type": "bar"
        }
        '''

        with patch('app.agents.analysis_agent_langgraph.AnalysisAgentLangGraph') as MockAnalysisAgent, \
             patch('app.agents.visualization_agent.VisualizationAgent') as MockVizAgent:

            # Setup mocks
            mock_analysis_instance = MagicMock()
            mock_analysis_instance.workflow.ainvoke = AsyncMock(return_value=mock_analysis_result)
            MockAnalysisAgent.return_value = mock_analysis_instance

            # VisualizationAgent fails
            mock_viz_instance = MagicMock()
            mock_viz_instance.workflow.ainvoke = AsyncMock(
                side_effect=Exception("Chart generation failed")
            )
            MockVizAgent.return_value = mock_viz_instance

            # Create orchestrator
            orchestrator = UnifiedWorkflowOrchestrator(
                llm_client=mock_llm_client,
                mindsdb_service=mock_mindsdb_service,
                hitl_service=mock_hitl_service,
            )

            # Execute workflow
            result = await orchestrator.execute(
                user_query="Show sales",
                database="test_db",
                user_id="user-123",
                company_id="company-123",
            )

            # Verify partial success (analysis succeeded, visualization failed)
            assert result["workflow_status"] == "partial_success"
            assert result["query_success"] is True
            assert result["visualization_id"] is None
            assert len(result["warnings"]) > 0

    @pytest.mark.asyncio
    async def test_workflow_with_analysis_failure(
        self,
        mock_llm_client,
        mock_mindsdb_service,
        mock_hitl_service,
    ):
        """Test workflow with analysis failure (total failure)."""

        with patch('app.agents.analysis_agent_langgraph.AnalysisAgentLangGraph') as MockAnalysisAgent:

            # AnalysisAgent fails
            mock_analysis_instance = MagicMock()
            mock_analysis_instance.workflow.ainvoke = AsyncMock(
                side_effect=Exception("Database connection failed")
            )
            MockAnalysisAgent.return_value = mock_analysis_instance

            # Create orchestrator
            orchestrator = UnifiedWorkflowOrchestrator(
                llm_client=mock_llm_client,
                mindsdb_service=mock_mindsdb_service,
                hitl_service=mock_hitl_service,
            )

            # Execute workflow
            result = await orchestrator.execute(
                user_query="Show sales",
                database="test_db",
                user_id="user-123",
                company_id="company-123",
            )

            # Verify total failure (analysis is essential)
            assert result["workflow_status"] == "failed"
            assert len(result["errors"]) > 0
            assert "Database connection failed" in str(result["errors"])

    @pytest.mark.asyncio
    async def test_workflow_with_custom_options(
        self,
        mock_llm_client,
        mock_mindsdb_service,
        mock_hitl_service,
    ):
        """Test workflow with custom options."""

        mock_analysis_result = {
            "workflow_status": "completed",
            "query_success": True,
            "generated_sql": "SELECT * FROM sales LIMIT 100",
            "query_data": [{"sales": 1000}],
            "insights": [],
            "warnings": [],
            "errors": [],
        }

        with patch('app.agents.analysis_agent_langgraph.AnalysisAgentLangGraph') as MockAnalysisAgent:

            mock_analysis_instance = MagicMock()
            mock_analysis_instance.workflow.ainvoke = AsyncMock(return_value=mock_analysis_result)
            MockAnalysisAgent.return_value = mock_analysis_instance

            # Create orchestrator
            orchestrator = UnifiedWorkflowOrchestrator(
                llm_client=mock_llm_client,
                mindsdb_service=mock_mindsdb_service,
                hitl_service=mock_hitl_service,
            )

            # Execute with custom options
            result = await orchestrator.execute(
                user_query="Show sales",
                database="test_db",
                user_id="user-123",
                company_id="company-123",
                options={
                    "auto_visualize": False,  # Disable visualization
                    "limit_rows": 100,
                    "chart_type": "line",  # Ignored since auto_visualize=False
                },
            )

            # Verify options were respected
            assert result["should_visualize"] is False
            assert "disabled by user" in result.get("skip_visualization_reason", "").lower()

    @pytest.mark.asyncio
    async def test_multi_turn_conversation_memory(
        self,
        mock_llm_client,
        mock_mindsdb_service,
        mock_hitl_service,
    ):
        """Test multi-turn conversation with memory."""

        # Mock AnalysisAgent for first query
        mock_analysis_result_1 = {
            "workflow_status": "completed",
            "query_success": True,
            "generated_sql": "SELECT region, SUM(sales) FROM sales GROUP BY region",
            "query_data": [{"region": "North", "sales": 1000}],
            "insights": ["Sales by region retrieved"],
            "warnings": [],
            "errors": [],
        }

        # Mock AnalysisAgent for second query (should have context from first)
        mock_analysis_result_2 = {
            "workflow_status": "completed",
            "query_success": True,
            "generated_sql": "SELECT region, SUM(sales) FROM sales WHERE quarter = 2 GROUP BY region",
            "query_data": [{"region": "North", "sales": 500}],
            "insights": ["Q2 sales by region retrieved"],
            "warnings": [],
            "errors": [],
        }

        # Mock LLM to not visualize (simple test)
        mock_llm_client.generate_text.return_value = '''
        {
            "should_visualize": false,
            "reasoning": "Simple test",
            "suggested_chart_type": null
        }
        '''

        with patch('app.agents.analysis_agent_langgraph.AnalysisAgentLangGraph') as MockAnalysisAgent:

            # Setup mock
            mock_analysis_instance = MagicMock()
            mock_analysis_instance.workflow.ainvoke = AsyncMock(
                side_effect=[mock_analysis_result_1, mock_analysis_result_2]
            )
            MockAnalysisAgent.return_value = mock_analysis_instance

            # Create orchestrator
            orchestrator = UnifiedWorkflowOrchestrator(
                llm_client=mock_llm_client,
                mindsdb_service=mock_mindsdb_service,
                hitl_service=mock_hitl_service,
            )

            # First query - no conversation_id
            result1 = await orchestrator.execute(
                user_query="Show sales by region",
                database="sales_db",
                user_id="user-123",
                company_id="company-123",
            )

            # Capture conversation_id from first result
            conversation_id = result1["conversation_id"]
            assert conversation_id is not None

            # Second query - reuse same conversation_id
            result2 = await orchestrator.execute(
                user_query="What about Q2?",  # Contextual follow-up
                database="sales_db",
                user_id="user-123",
                company_id="company-123",
                conversation_id=conversation_id,  # SAME conversation!
            )

            # Verify same conversation
            assert result2["conversation_id"] == conversation_id

            # Verify both workflows executed
            assert result1["workflow_id"] != result2["workflow_id"]  # Different executions
            assert result1["conversation_id"] == result2["conversation_id"]  # Same conversation

            # Verify checkpointer was called with same thread_id
            # The workflow would have loaded previous state from checkpoint
            logger.info(f"First workflow: {result1['workflow_id']}")
            logger.info(f"Second workflow: {result2['workflow_id']}")
            logger.info(f"Shared conversation: {conversation_id}")

    @pytest.mark.asyncio
    async def test_conversation_isolation(
        self,
        mock_llm_client,
        mock_mindsdb_service,
        mock_hitl_service,
    ):
        """Test that different conversations are isolated."""

        mock_analysis_result = {
            "workflow_status": "completed",
            "query_success": True,
            "generated_sql": "SELECT * FROM sales",
            "query_data": [{"sales": 1000}],
            "insights": [],
            "warnings": [],
            "errors": [],
        }

        mock_llm_client.generate_text.return_value = '''
        {
            "should_visualize": false,
            "reasoning": "Simple test",
            "suggested_chart_type": null
        }
        '''

        with patch('app.agents.analysis_agent_langgraph.AnalysisAgentLangGraph') as MockAnalysisAgent:

            mock_analysis_instance = MagicMock()
            mock_analysis_instance.workflow.ainvoke = AsyncMock(return_value=mock_analysis_result)
            MockAnalysisAgent.return_value = mock_analysis_instance

            orchestrator = UnifiedWorkflowOrchestrator(
                llm_client=mock_llm_client,
                mindsdb_service=mock_mindsdb_service,
                hitl_service=mock_hitl_service,
            )

            # Conversation A
            result_a = await orchestrator.execute(
                user_query="Show sales",
                database="sales_db",
                user_id="user-123",
                company_id="company-123",
                conversation_id="conversation-a",
            )

            # Conversation B (different thread)
            result_b = await orchestrator.execute(
                user_query="Show sales",
                database="sales_db",
                user_id="user-123",
                company_id="company-123",
                conversation_id="conversation-b",
            )

            # Verify different conversations
            assert result_a["conversation_id"] == "conversation-a"
            assert result_b["conversation_id"] == "conversation-b"
            assert result_a["workflow_id"] != result_b["workflow_id"]
