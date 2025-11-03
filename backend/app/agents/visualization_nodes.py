"""
Visualization Workflow Nodes

LangGraph workflow nodes for VisualizationAgent.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from app.agents.visualization_state import VisualizationState
from app.core.llm import LLMClient
from app.tools.visualization_tools import (
    recommend_chart_type,
    create_plotly_figure,
    apply_plotly_theme,
    generate_chart_insights,
)

logger = logging.getLogger(__name__)


# ============================================
# Node 1: Recommend Chart Type
# ============================================

async def recommend_chart_node(
    state: VisualizationState,
    llm_client: LLMClient,
) -> Dict[str, Any]:
    """
    Recommend best chart type using LLM + rules.

    Updates state:
    - recommended_chart_type
    - chart_recommendation_reasoning
    - recommendation_confidence
    - alternative_chart_types
    - chart_type (if not already specified by user)
    """
    logger.info("[Node: recommend_chart] Starting chart type recommendation")

    try:
        # If user already specified chart type, skip recommendation
        if state.get("chart_type"):
            logger.info(f"[Node: recommend_chart] User specified chart type: {state['chart_type']}")
            return {
                "workflow_status": "recommending",
                "recommended_chart_type": state["chart_type"],
                "chart_recommendation_reasoning": "User specified chart type",
                "recommendation_confidence": 1.0,
                "alternative_chart_types": [],
            }

        # Get recommendation
        recommendation = await recommend_chart_type(
            data=state["data"],
            user_query=state["user_query"],
            analysis_results=state.get("analysis_results"),
            llm_client=llm_client,
        )

        logger.info(
            f"[Node: recommend_chart] Recommended: {recommendation.recommended_type} "
            f"(confidence: {recommendation.confidence})"
        )

        return {
            "workflow_status": "recommending",
            "recommended_chart_type": recommendation.recommended_type,
            "chart_recommendation_reasoning": recommendation.reasoning,
            "recommendation_confidence": recommendation.confidence,
            "alternative_chart_types": recommendation.alternatives,
            "chart_type": recommendation.recommended_type,  # Set as final chart type
        }

    except Exception as e:
        logger.error(f"[Node: recommend_chart] Failed: {e}")
        return {
            "errors": [f"Chart recommendation failed: {str(e)}"],
            "workflow_status": "failed",
            "chart_type": "bar",  # Safe fallback
            "recommended_chart_type": "bar",
            "chart_recommendation_reasoning": f"Error in recommendation: {str(e)}",
            "recommendation_confidence": 0.5,
        }


# ============================================
# Node 2: Create Plotly Figure
# ============================================

async def create_plotly_figure_node(
    state: VisualizationState,
    llm_client: LLMClient,
) -> Dict[str, Any]:
    """
    Create Plotly figure from data.

    Uses create_plotly_figure() tool which handles all chart types.

    Updates state:
    - plotly_figure (as dict)
    - errors (if creation fails)
    """
    logger.info(f"[Node: create_plotly_figure] Creating {state['chart_type']} chart")

    try:
        # Create Plotly figure
        fig = await create_plotly_figure(
            data=state["data"],
            chart_type=state["chart_type"],
            user_query=state["user_query"],
            analysis_results=state.get("analysis_results"),
            llm_client=llm_client,
        )

        # Convert figure to dict for state storage
        plotly_figure_dict = fig.to_dict()

        logger.info(f"[Node: create_plotly_figure] Successfully created {state['chart_type']} chart")

        return {
            "workflow_status": "creating",
            "plotly_figure": plotly_figure_dict,
        }

    except Exception as e:
        logger.error(f"[Node: create_plotly_figure] Failed: {e}")
        return {
            "errors": [f"Failed to create Plotly figure: {str(e)}"],
            "workflow_status": "failed",
        }


# ============================================
# Node 3: Apply Theme
# ============================================

async def apply_theme_node(
    state: VisualizationState,
) -> Dict[str, Any]:
    """
    Apply Plotly theme and custom styling.

    Supports:
    - Built-in Plotly themes
    - Custom style profiles (loaded from database)
    - Logo placement
    - Watermarks
    - Ad-hoc customizations

    Updates state:
    - plotly_figure (updated with styling)
    """
    logger.info(f"[Node: apply_theme] Applying theme: {state['plotly_theme']}")

    try:
        # Get figure from state
        import plotly.graph_objects as go
        fig = go.Figure(state["plotly_figure"])

        # Apply theme with custom profile and customizations
        fig = await apply_plotly_theme(
            fig=fig,
            theme=state.get("plotly_theme", "plotly"),
            custom_profile=state.get("custom_style_profile"),  # Loaded from DB if available
            customizations=state.get("theme_customizations"),
        )

        # Convert back to dict
        plotly_figure_dict = fig.to_dict()

        logger.info("[Node: apply_theme] Theme applied successfully")

        return {
            "workflow_status": "styling",
            "plotly_figure": plotly_figure_dict,
        }

    except Exception as e:
        logger.error(f"[Node: apply_theme] Failed: {e}")
        # Non-fatal error - return figure as-is
        return {
            "warnings": [f"Theme application failed: {str(e)}, using default styling"],
            "workflow_status": "styling",
        }


# ============================================
# Node 4: Generate Insights (Optional)
# ============================================

async def generate_insights_node(
    state: VisualizationState,
    llm_client: LLMClient,
) -> Dict[str, Any]:
    """
    Generate natural language insights about the visualization.

    Uses LLM to analyze data and chart to produce meaningful insights.

    Updates state:
    - chart_insights (accumulated)
    - completed_at
    - workflow_status: "completed"
    """
    logger.info("[Node: generate_insights] Generating chart insights")

    try:
        # Generate insights
        insights = await generate_chart_insights(
            data=state["data"],
            chart_type=state["chart_type"],
            chart_config=state.get("plotly_figure", {}),
            analysis_results=state.get("analysis_results"),
            llm_client=llm_client,
        )

        logger.info(f"[Node: generate_insights] Generated {len(insights)} insights")

        return {
            "chart_insights": insights,
            "workflow_status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"[Node: generate_insights] Failed: {e}")
        # Non-fatal - still mark as completed
        return {
            "warnings": [f"Insight generation failed: {str(e)}"],
            "workflow_status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
        }


# ============================================
# Conditional Edge Functions
# ============================================

def should_generate_insights(state: VisualizationState) -> str:
    """
    Determine if insights should be generated.

    Checks user options to see if insights are requested.

    Args:
        state: Current workflow state

    Returns:
        Next node name: "generate_insights" or "end"
    """
    include_insights = state.get("options", {}).get("include_insights", True)

    if include_insights:
        logger.info("[Router] Routing to generate_insights node")
        return "generate_insights"
    else:
        logger.info("[Router] Skipping insights, routing to end")
        # Mark as completed here if skipping insights
        return "end"


def route_after_theme(state: VisualizationState) -> str:
    """
    Route after theme application.

    Wrapper for should_generate_insights with proper state updates.

    Args:
        state: Current workflow state

    Returns:
        Next node name: "generate_insights" or "end"
    """
    return should_generate_insights(state)
