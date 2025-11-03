"""
Integration tests for enhanced analysis workflow.

Tests the complete flow from user query to enhanced analysis results.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.analysis_agent_langgraph import AnalysisAgentLangGraph, create_analysis_agent_langgraph
from app.agents.workflow_state import create_initial_state
from app.agents.workflow_nodes import enhanced_analysis_node, should_do_enhanced_analysis
from app.core.llm import LLMClient


@pytest.mark.asyncio
async def test_enhanced_analysis_node_with_correlation_query():
    """Test enhanced_analysis_node when user asks about correlation."""

    # Mock LLM client
    llm_client = AsyncMock(spec=LLMClient)

    # Mock LLM response - decides to run correlation_analysis
    mock_llm_response = MagicMock()
    mock_llm_response.content = """
    {
        "tools_to_run": ["correlation_analysis"],
        "reasoning": "User explicitly asked about correlation between columns"
    }
    """
    llm_client.chat_completion_with_system.return_value = mock_llm_response

    # Create test state
    state = {
        "query": "Is there a correlation between price and sales?",
        "query_data": [
            {"price": 10, "sales": 100},
            {"price": 20, "sales": 200},
            {"price": 30, "sales": 300},
            {"price": 40, "sales": 400},
            {"price": 50, "sales": 500},
        ],
        "analysis_results": {"summary_stats": {}},
        "query_success": True,
    }

    # Execute enhanced analysis node
    result = await enhanced_analysis_node(state, llm_client)

    # Assertions
    assert result["enhanced_analysis"] is not None
    assert "correlation_analysis" in result["enhanced_analysis"]["tools_used"]
    assert "results" in result["enhanced_analysis"]
    assert "correlation_analysis" in result["enhanced_analysis"]["results"]

    # Check correlation results
    corr_results = result["enhanced_analysis"]["results"]["correlation_analysis"]
    assert "correlation_matrix" in corr_results
    assert "significant_correlations" in corr_results
    assert corr_results["method"] == "pearson"
    assert corr_results["sample_size"] == 5

    # Should find strong correlation between price and sales
    assert len(corr_results["significant_correlations"]) > 0

    # Check insights were generated
    assert "insights" in result
    assert len(result["insights"]) > 0
    assert "correlation" in result["insights"][0].lower()


@pytest.mark.asyncio
async def test_enhanced_analysis_node_without_correlation_query():
    """Test enhanced_analysis_node when no additional analysis needed."""

    # Mock LLM client
    llm_client = AsyncMock(spec=LLMClient)

    # Mock LLM response - no tools needed
    mock_llm_response = MagicMock()
    mock_llm_response.content = """
    {
        "tools_to_run": [],
        "reasoning": "Simple data retrieval, no additional analysis needed"
    }
    """
    llm_client.chat_completion_with_system.return_value = mock_llm_response

    # Create test state
    state = {
        "query": "Show me all users",
        "query_data": [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ],
        "analysis_results": {"summary_stats": {}},
        "query_success": True,
    }

    # Execute enhanced analysis node
    result = await enhanced_analysis_node(state, llm_client)

    # Assertions
    assert result["enhanced_analysis"] is None


@pytest.mark.asyncio
async def test_enhanced_analysis_node_with_empty_data():
    """Test enhanced_analysis_node with empty data."""

    llm_client = AsyncMock(spec=LLMClient)

    state = {
        "query": "Is there correlation between X and Y?",
        "query_data": [],
        "analysis_results": {"summary_stats": {}},
        "query_success": True,
    }

    result = await enhanced_analysis_node(state, llm_client)

    # Should return None when no data
    assert result["enhanced_analysis"] is None


@pytest.mark.asyncio
async def test_enhanced_analysis_node_handles_tool_error():
    """Test enhanced_analysis_node handles tool execution errors gracefully."""

    # Mock LLM client
    llm_client = AsyncMock(spec=LLMClient)

    # Mock LLM response - decides to run correlation_analysis
    mock_llm_response = MagicMock()
    mock_llm_response.content = """
    {
        "tools_to_run": ["correlation_analysis"],
        "reasoning": "User asked about correlation"
    }
    """
    llm_client.chat_completion_with_system.return_value = mock_llm_response

    # Create state with insufficient data (will cause error)
    state = {
        "query": "Is there correlation between X and Y?",
        "query_data": [
            {"text": "not numeric"},
        ],
        "analysis_results": {"summary_stats": {}},
        "query_success": True,
    }

    # Execute enhanced analysis node
    result = await enhanced_analysis_node(state, llm_client)

    # Should handle error gracefully
    assert result["enhanced_analysis"] is not None
    assert "correlation_analysis" in result["enhanced_analysis"]["results"]

    # Error should be recorded but not crash
    corr_results = result["enhanced_analysis"]["results"]["correlation_analysis"]
    # Either returns empty results with warnings or error field
    assert "warnings" in corr_results or "error" in corr_results


def test_should_do_enhanced_analysis_router():
    """Test the router function that decides whether to run enhanced analysis."""

    # Should run when all conditions met
    state_run = {
        "query_success": True,
        "query_data": [{"a": 1}],
        "analysis_results": {"summary_stats": {}},
    }
    assert should_do_enhanced_analysis(state_run) == "enhanced_analysis"

    # Should skip when query failed
    state_failed = {
        "query_success": False,
        "query_data": [{"a": 1}],
        "analysis_results": {"summary_stats": {}},
    }
    assert should_do_enhanced_analysis(state_failed) == "end"

    # Should skip when no data
    state_no_data = {
        "query_success": True,
        "query_data": [],
        "analysis_results": {"summary_stats": {}},
    }
    assert should_do_enhanced_analysis(state_no_data) == "end"

    # Should skip when analysis not completed
    state_no_analysis = {
        "query_success": True,
        "query_data": [{"a": 1}],
        "analysis_results": None,
    }
    assert should_do_enhanced_analysis(state_no_analysis) == "end"


@pytest.mark.asyncio
async def test_enhanced_analysis_node_llm_prompt():
    """Test that LLM receives correct prompt with context."""

    # Mock LLM client
    llm_client = AsyncMock(spec=LLMClient)

    mock_llm_response = MagicMock()
    mock_llm_response.content = '{"tools_to_run": [], "reasoning": "test"}'
    llm_client.chat_completion_with_system.return_value = mock_llm_response

    state = {
        "query": "Test query about correlation",
        "query_data": [{"x": 1, "y": 2}],
        "analysis_results": {"summary_stats": {}},
        "query_success": True,
    }

    await enhanced_analysis_node(state, llm_client)

    # Verify LLM was called
    assert llm_client.chat_completion_with_system.called

    # Check prompt includes key information
    call_args = llm_client.chat_completion_with_system.call_args
    assert "correlation" in call_args.kwargs["user_message"].lower()
    assert "Test query about correlation" in call_args.kwargs["user_message"]
    assert "correlation_analysis" in call_args.kwargs["user_message"]


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires real LLM and MindsDB - manual testing only")
async def test_full_workflow_with_correlation_query():
    """
    Full end-to-end test with real agent.

    This test requires:
    - Real Azure OpenAI credentials
    - Real MindsDB connection
    - Manual execution only
    """

    # Create agent
    agent = create_analysis_agent_langgraph()

    # Process query
    result = await agent.process_query_async(
        query="Is there a correlation between price and sales volume?",
        database="test_database",
        session_id="test-session-123",
    )

    # Verify workflow completed
    assert result["workflow_status"] == "completed"
    assert result["query_success"] is True

    # Verify basic analysis ran
    assert result["analysis_results"] is not None

    # Verify enhanced analysis ran
    assert result["enhanced_analysis"] is not None
    assert "correlation_analysis" in result["enhanced_analysis"]["tools_used"]

    # Verify insights were added
    assert len(result["insights"]) > 0

    # Verify correlation results
    corr_results = result["enhanced_analysis"]["results"]["correlation_analysis"]
    assert "correlation_matrix" in corr_results
    assert "significant_correlations" in corr_results


@pytest.mark.asyncio
async def test_enhanced_analysis_with_non_numeric_data():
    """Test enhanced analysis with data that has no numeric columns."""

    llm_client = AsyncMock(spec=LLMClient)

    mock_llm_response = MagicMock()
    mock_llm_response.content = """
    {
        "tools_to_run": ["correlation_analysis"],
        "reasoning": "User asked about correlation"
    }
    """
    llm_client.chat_completion_with_system.return_value = mock_llm_response

    # Data with no numeric columns
    state = {
        "query": "Is there correlation?",
        "query_data": [
            {"name": "Alice", "city": "NYC"},
            {"name": "Bob", "city": "LA"},
            {"name": "Charlie", "city": "SF"},
        ],
        "analysis_results": {"summary_stats": {}},
        "query_success": True,
    }

    result = await enhanced_analysis_node(state, llm_client)

    # Should handle gracefully
    assert result["enhanced_analysis"] is not None
    corr_results = result["enhanced_analysis"]["results"]["correlation_analysis"]

    # Should have warnings about insufficient numeric columns
    assert "warnings" in corr_results or len(corr_results.get("columns_analyzed", [])) == 0


@pytest.mark.asyncio
async def test_llm_returns_invalid_json():
    """Test handling when LLM returns invalid JSON."""

    llm_client = AsyncMock(spec=LLMClient)

    # Mock LLM response with invalid JSON
    mock_llm_response = MagicMock()
    mock_llm_response.content = "This is not valid JSON at all!"
    llm_client.chat_completion_with_system.return_value = mock_llm_response

    state = {
        "query": "Test query",
        "query_data": [{"x": 1}],
        "analysis_results": {"summary_stats": {}},
        "query_success": True,
    }

    result = await enhanced_analysis_node(state, llm_client)

    # Should handle gracefully and return None
    assert result["enhanced_analysis"] is None


@pytest.mark.asyncio
async def test_multiple_numeric_columns_correlation():
    """Test correlation analysis with multiple numeric columns."""

    llm_client = AsyncMock(spec=LLMClient)

    mock_llm_response = MagicMock()
    mock_llm_response.content = """
    {
        "tools_to_run": ["correlation_analysis"],
        "reasoning": "Multiple numeric columns present"
    }
    """
    llm_client.chat_completion_with_system.return_value = mock_llm_response

    # Data with 3 numeric columns
    state = {
        "query": "Analyze relationships",
        "query_data": [
            {"price": 10, "sales": 100, "rating": 4.5},
            {"price": 20, "sales": 200, "rating": 4.8},
            {"price": 30, "sales": 300, "rating": 4.2},
            {"price": 40, "sales": 400, "rating": 4.9},
            {"price": 50, "sales": 500, "rating": 4.7},
        ],
        "analysis_results": {"summary_stats": {}},
        "query_success": True,
    }

    result = await enhanced_analysis_node(state, llm_client)

    # Should analyze all numeric columns
    assert result["enhanced_analysis"] is not None
    corr_results = result["enhanced_analysis"]["results"]["correlation_analysis"]

    assert len(corr_results["columns_analyzed"]) == 3
    assert "price" in corr_results["columns_analyzed"]
    assert "sales" in corr_results["columns_analyzed"]
    assert "rating" in corr_results["columns_analyzed"]

    # Correlation matrix should be 3x3
    assert len(corr_results["correlation_matrix"]) == 3
