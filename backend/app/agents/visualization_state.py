"""
Visualization Workflow State

State management for VisualizationAgent workflow using LangGraph.
"""

from typing import TypedDict, Optional, Dict, Any, List, Annotated
from operator import add


class VisualizationState(TypedDict):
    """State for visualization workflow."""

    # Input from AnalysisAgent
    visualization_id: str
    session_id: str  # Link to AnalysisSession
    user_query: str  # Original user query for context
    data: List[Dict[str, Any]]  # Data from AnalysisAgent
    analysis_results: Optional[Dict[str, Any]]  # From AnalysisAgent

    # User options
    options: Dict[str, Any]  # User preferences and overrides

    # Workflow state
    workflow_status: str  # pending, recommending, creating, styling, completed, failed

    # Chart recommendation
    recommended_chart_type: Optional[str]  # bar, line, pie, scatter, etc.
    chart_recommendation_reasoning: Optional[str]  # Why this chart type
    recommendation_confidence: Optional[float]  # 0.0-1.0
    alternative_chart_types: List[str]  # Other suitable chart types

    # Plotly figure
    plotly_figure: Optional[Dict[str, Any]]  # Plotly figure as dict (for state)
    chart_type: Optional[str]  # Final selected type (bar, line, pie, etc.)

    # Styling
    plotly_theme: Optional[str]  # plotly, plotly_white, plotly_dark, custom
    custom_style_profile_id: Optional[str]  # Link to CustomStyleProfile
    custom_style_profile: Optional[Dict[str, Any]]  # Loaded profile data
    theme_customizations: Optional[Dict[str, Any]]  # Ad-hoc style overrides
    user_chart_template: Optional[Dict[str, Any]]  # User's chart template from preferences

    # Insights
    chart_insights: Annotated[List[str], add]  # Accumulated insights

    # Metadata
    created_at: str
    completed_at: Optional[str]

    # Error handling
    errors: Annotated[List[str], add]  # Accumulated errors
    warnings: Annotated[List[str], add]  # Accumulated warnings


def create_initial_visualization_state(
    visualization_id: str,
    session_id: str,
    user_query: str,
    data: List[Dict[str, Any]],
    analysis_results: Optional[Dict[str, Any]] = None,
    chart_type: Optional[str] = None,
    plotly_theme: str = "plotly",
    custom_style_profile_id: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
    user_chart_template: Optional[Dict[str, Any]] = None,
) -> VisualizationState:
    """
    Create initial visualization state.

    Args:
        visualization_id: Unique visualization ID
        session_id: Analysis session ID
        user_query: Original user query
        data: Query results from AnalysisAgent
        analysis_results: Optional analysis results
        chart_type: Optional user-specified chart type
        plotly_theme: Base Plotly theme
        custom_style_profile_id: Optional custom style profile ID
        options: User options and preferences
        user_chart_template: User's chart template from preferences

    Returns:
        Initial VisualizationState
    """
    from datetime import datetime

    return VisualizationState(
        # Input
        visualization_id=visualization_id,
        session_id=session_id,
        user_query=user_query,
        data=data,
        analysis_results=analysis_results,
        options=options or {},

        # Workflow state
        workflow_status="pending",

        # Chart recommendation
        recommended_chart_type=chart_type,  # May be pre-specified
        chart_recommendation_reasoning=None,
        recommendation_confidence=None,
        alternative_chart_types=[],

        # Plotly figure
        plotly_figure=None,
        chart_type=chart_type,  # May be pre-specified

        # Styling
        plotly_theme=plotly_theme,
        custom_style_profile_id=custom_style_profile_id,
        custom_style_profile=None,
        theme_customizations=options.get("style_overrides") if options else None,
        user_chart_template=user_chart_template,

        # Insights
        chart_insights=[],

        # Metadata
        created_at=datetime.utcnow().isoformat(),
        completed_at=None,

        # Error handling
        errors=[],
        warnings=[],
    )
