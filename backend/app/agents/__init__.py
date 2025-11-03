"""
Agent implementations for the Agentic BI platform.

This module provides LangGraph-based agent implementations with:
- State-based workflow orchestration
- Human-in-the-loop integration
- Conditional routing
- Built-in checkpointing and resume
- Langfuse tracing integration
"""

# LangGraph-based Analysis Agent
from app.agents.analysis_agent_langgraph import (
    AnalysisAgentLangGraph,
    create_analysis_agent,
)

# Workflow state definition
from app.agents.workflow_state import WorkflowState, create_initial_state

# Workflow node functions
from app.agents.workflow_nodes import (
    explore_schema_node,
    generate_sql_node,
    human_review_node,
    validate_sql_node,
    execute_query_node,
    analyze_results_node,
    should_request_human_review,
    should_proceed_after_validation,
    should_analyze_results,
)

# Visualization Agent
from app.agents.visualization_agent import (
    VisualizationAgent,
    create_visualization_agent,
)

# Visualization state
from app.agents.visualization_state import (
    VisualizationState,
    create_initial_visualization_state,
)

# Visualization nodes
from app.agents.visualization_nodes import (
    recommend_chart_node,
    create_plotly_figure_node,
    apply_theme_node,
    generate_insights_node,
    should_generate_insights,
)

__all__ = [
    # Primary agent implementation
    "AnalysisAgentLangGraph",
    "create_analysis_agent",
    # State management
    "WorkflowState",
    "create_initial_state",
    # Workflow nodes
    "explore_schema_node",
    "generate_sql_node",
    "human_review_node",
    "validate_sql_node",
    "execute_query_node",
    "analyze_results_node",
    # Conditional functions
    "should_request_human_review",
    "should_proceed_after_validation",
    "should_analyze_results",
    # Visualization agent
    "VisualizationAgent",
    "create_visualization_agent",
    # Visualization state
    "VisualizationState",
    "create_initial_visualization_state",
    # Visualization nodes
    "recommend_chart_node",
    "create_plotly_figure_node",
    "apply_theme_node",
    "generate_insights_node",
    "should_generate_insights",
]
