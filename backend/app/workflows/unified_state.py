"""
Unified workflow state for multi-agent coordination.

This module defines the state structure for unified workflows that
coordinate multiple agents (AnalysisAgent, VisualizationAgent).
"""

from typing import TypedDict, Optional, Dict, Any, List, Annotated
from operator import add


class UnifiedWorkflowState(TypedDict):
    """
    Unified state for multi-agent workflow.

    Combines state from both AnalysisAgent and VisualizationAgent,
    plus coordination metadata for workflow orchestration.

    The state flows through multiple nodes:
    1. run_analysis_adapter: Invokes AnalysisAgent subgraph
    2. decide_visualization: Determines if visualization is needed
    3. run_visualization_adapter: Invokes VisualizationAgent subgraph (conditional)
    4. aggregate_results: Combines results from all agents

    Annotated fields with `add` operator accumulate values across nodes
    (e.g., insights from multiple agents are concatenated).
    """

    # === Request ===
    workflow_id: str  # Unique per execution
    conversation_id: str  # Persistent across conversation (thread_id for checkpointer)
    user_query: str
    database: str
    options: Dict[str, Any]

    # === User Context ===
    user_id: str
    company_id: str

    # === Workflow Control ===
    workflow_status: str  # pending, analyzing, deciding, visualizing, completed, failed
    workflow_stage: Optional[str]  # init, analyzing, deciding, visualizing, aggregating, completed
    current_agent: Optional[str]  # analysis, visualization

    # === AnalysisAgent State (embedded) ===
    analysis_session_id: Optional[str]
    schema: Optional[Dict[str, Any]]
    generated_sql: Optional[str]
    sql_confidence: Optional[float]
    query_success: bool
    query_data: Optional[List[Dict[str, Any]]]
    analysis_results: Optional[Dict[str, Any]]
    enhanced_analysis: Optional[Dict[str, Any]]

    # === Visualization Decision ===
    should_visualize: bool
    visualization_reasoning: Optional[str]
    skip_visualization_reason: Optional[str]

    # === VisualizationAgent State (embedded) ===
    visualization_id: Optional[str]
    recommended_chart_type: Optional[str]
    chart_type: Optional[str]
    plotly_figure: Optional[Dict[str, Any]]
    chart_insights: Annotated[List[str], add]

    # === Aggregated Results ===
    insights: Annotated[List[str], add]  # Accumulated from all agents
    recommendations: Annotated[List[str], add]

    # === Error Handling ===
    errors: Annotated[List[str], add]
    warnings: Annotated[List[str], add]
    partial_success: bool

    # === Metadata ===
    created_at: str
    completed_at: Optional[str]
    execution_time_ms: Optional[int]
    agents_executed: Annotated[List[str], add]
