"""
API Schemas for Unified Workflow.

Request and response models for the unified multi-agent workflow API.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
import numpy as np
import json


def convert_numpy_types(obj):
    """
    Convert numpy types to Python native types for JSON serialization.

    Args:
        obj: Object that may contain numpy types

    Returns:
        Object with numpy types converted to Python types
    """
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    return obj


# === Request Schemas ===

class UnifiedWorkflowOptions(BaseModel):
    """
    Options for unified workflow execution.

    Controls behavior of both AnalysisAgent and VisualizationAgent.
    """

    # Analysis options
    limit_rows: int = Field(
        default=1000,
        ge=1,
        le=10000,
        description="Maximum rows to return from query"
    )
    include_analysis: bool = Field(
        default=True,
        description="Include statistical analysis of results"
    )

    # Visualization options
    auto_visualize: bool = Field(
        default=True,
        description="Automatically create visualization if appropriate"
    )
    chart_type: Optional[str] = Field(
        default=None,
        description="Force specific chart type (bar, line, pie, scatter, heatmap, table)"
    )
    plotly_theme: str = Field(
        default="plotly",
        description="Base Plotly theme (plotly, plotly_white, plotly_dark)"
    )
    custom_style_profile_id: Optional[str] = Field(
        default=None,
        description="Custom style profile ID for branding"
    )
    include_insights: bool = Field(
        default=True,
        description="Generate AI-powered insights"
    )

    # Performance options
    cache_results: bool = Field(
        default=True,
        description="Enable result caching (future feature)"
    )
    timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Workflow timeout in seconds"
    )


class UnifiedWorkflowRequest(BaseModel):
    """Request for unified workflow execution."""

    query: str = Field(
        ...,
        min_length=1,
        description="Natural language query to execute"
    )
    database: str = Field(
        ...,
        min_length=1,
        description="Target database name"
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Conversation thread ID for multi-turn conversations. "
                    "Provide the same ID for follow-up questions to maintain context."
    )
    options: UnifiedWorkflowOptions = Field(
        default_factory=UnifiedWorkflowOptions,
        description="Workflow options"
    )


# === Response Schemas ===

class AnalysisResults(BaseModel):
    """Analysis portion of unified workflow results."""

    session_id: str = Field(..., description="Analysis session ID")
    generated_sql: Optional[str] = Field(None, description="Generated SQL query")
    sql_confidence: Optional[float] = Field(None, description="SQL generation confidence (0-1)")
    row_count: int = Field(default=0, description="Number of rows returned")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="Query results")
    analysis_summary: Optional[Dict[str, Any]] = Field(None, description="Statistical analysis summary")
    enhanced_analysis: Optional[Dict[str, Any]] = Field(None, description="Enhanced analysis (correlations, trends, etc.)")


class VisualizationResults(BaseModel):
    """Visualization portion of unified workflow results."""

    visualization_id: str = Field(..., description="Visualization ID")
    chart_type: str = Field(..., description="Chart type (bar, line, pie, etc.)")
    plotly_figure: Dict[str, Any] = Field(..., description="Complete Plotly figure JSON")
    chart_recommendation_reasoning: Optional[str] = Field(None, description="Why this chart type was chosen")
    recommendation_confidence: Optional[float] = Field(None, description="Recommendation confidence (0-1)")
    insights: List[str] = Field(default_factory=list, description="Chart-specific insights")


class WorkflowMetadata(BaseModel):
    """Metadata about workflow execution."""

    workflow_id: str = Field(..., description="Unique workflow execution ID")
    conversation_id: str = Field(..., description="Conversation thread ID for multi-turn memory")
    workflow_status: str = Field(..., description="completed | partial_success | failed")
    workflow_stage: Optional[str] = Field(None, description="Last completed stage")
    agents_executed: List[str] = Field(default_factory=list, description="List of agents that executed")
    execution_time_ms: int = Field(..., description="Total execution time in milliseconds")
    created_at: datetime = Field(..., description="Workflow start time")
    completed_at: datetime = Field(..., description="Workflow completion time")


class UnifiedWorkflowResponse(BaseModel):
    """Complete unified workflow response."""

    # Metadata
    metadata: WorkflowMetadata

    # Analysis results (always present if workflow started)
    analysis: Optional[AnalysisResults] = Field(None, description="Analysis results")

    # Visualization results (present if visualization was created)
    visualization: Optional[VisualizationResults] = Field(None, description="Visualization results")

    # Combined insights from all agents
    insights: List[str] = Field(default_factory=list, description="Combined insights")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")

    # Error handling
    errors: List[str] = Field(default_factory=list, description="Errors encountered")
    warnings: List[str] = Field(default_factory=list, description="Warnings")

    # Decision tracking
    should_visualize: bool = Field(default=False, description="Whether visualization was attempted")
    visualization_reasoning: Optional[str] = Field(None, description="Why visualization was/wasn't created")


class WorkflowStatusResponse(BaseModel):
    """Response for workflow status check."""

    workflow_id: str
    status: str  # pending, analyzing, deciding, visualizing, completed, failed, partial_success
    stage: Optional[str] = None  # Current workflow stage
    progress: Optional[Dict[str, Any]] = None  # Progress information (future feature)


class WorkflowListItem(BaseModel):
    """Summary of a workflow for list views."""

    workflow_id: str
    user_query: str
    database: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    execution_time_ms: Optional[int] = None


class WorkflowListResponse(BaseModel):
    """Response for workflow history list."""

    workflows: List[WorkflowListItem]
    total: int
    page: int = 1
    page_size: int = 50


# === Helper Functions ===

def create_unified_workflow_response(
    workflow_state: Dict[str, Any]
) -> UnifiedWorkflowResponse:
    """
    Create UnifiedWorkflowResponse from workflow state.

    Args:
        workflow_state: Final state from UnifiedWorkflowOrchestrator

    Returns:
        UnifiedWorkflowResponse
    """
    # Convert any numpy types to Python native types for JSON serialization
    workflow_state = convert_numpy_types(workflow_state)

    # Create metadata
    metadata = WorkflowMetadata(
        workflow_id=workflow_state["workflow_id"],
        conversation_id=workflow_state["conversation_id"],
        workflow_status=workflow_state.get("workflow_status", "unknown"),
        workflow_stage=workflow_state.get("workflow_stage"),
        agents_executed=workflow_state.get("agents_executed", []),
        execution_time_ms=workflow_state.get("execution_time_ms", 0),
        created_at=datetime.fromisoformat(workflow_state["created_at"]),
        completed_at=datetime.fromisoformat(workflow_state.get("completed_at", workflow_state["created_at"])),
    )

    # Create analysis results if available
    analysis = None
    if workflow_state.get("query_success") or workflow_state.get("generated_sql"):
        analysis = AnalysisResults(
            session_id=workflow_state.get("analysis_session_id", workflow_state["workflow_id"]),
            generated_sql=workflow_state.get("generated_sql"),
            sql_confidence=workflow_state.get("sql_confidence"),
            row_count=len(workflow_state.get("query_data", [])),
            data=workflow_state.get("query_data", []),
            analysis_summary=workflow_state.get("analysis_results"),
            enhanced_analysis=workflow_state.get("enhanced_analysis"),
        )

    # Create visualization results if available
    visualization = None
    if workflow_state.get("plotly_figure") and workflow_state.get("visualization_id"):
        visualization = VisualizationResults(
            visualization_id=workflow_state["visualization_id"],
            chart_type=workflow_state.get("chart_type", "bar"),
            plotly_figure=workflow_state["plotly_figure"],
            chart_recommendation_reasoning=workflow_state.get("visualization_reasoning"),
            recommendation_confidence=workflow_state.get("recommendation_confidence"),
            insights=workflow_state.get("chart_insights", []),
        )

    return UnifiedWorkflowResponse(
        metadata=metadata,
        analysis=analysis,
        visualization=visualization,
        insights=workflow_state.get("insights", []),
        recommendations=workflow_state.get("recommendations", []),
        errors=workflow_state.get("errors", []),
        warnings=workflow_state.get("warnings", []),
        should_visualize=workflow_state.get("should_visualize", False),
        visualization_reasoning=workflow_state.get("visualization_reasoning") or workflow_state.get("skip_visualization_reason"),
    )
