"""
Visualization Agent

LangGraph-based agent for generating visualizations from data.
"""

import logging
from typing import Optional, Dict, Any
from uuid import uuid4

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langfuse.langchain import CallbackHandler

from app.agents.visualization_state import VisualizationState, create_initial_visualization_state
from app.agents.visualization_nodes import (
    recommend_chart_node,
    create_plotly_figure_node,
    apply_theme_node,
    generate_insights_node,
    route_after_theme,
)
from app.core.llm import LLMClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class VisualizationAgent:
    """
    LangGraph-based Visualization Agent.

    Workflow:
    START → recommend_chart → create_plotly_figure → apply_theme → [generate_insights?] → END

    Features:
    - Plotly-based chart generation
    - Intelligent chart type recommendation
    - Custom styling with enterprise branding
    - Logo and watermark support
    - AI-powered insights generation
    - Langfuse observability
    - Checkpointing for resume capability
    """

    def __init__(
        self,
        llm_client: LLMClient,
        langfuse_handler: Optional[CallbackHandler] = None,
    ):
        """
        Initialize VisualizationAgent.

        Args:
            llm_client: LLM client for recommendations and insights
            langfuse_handler: Optional Langfuse callback handler
        """
        self.llm_client = llm_client
        self.langfuse_handler = langfuse_handler
        self.workflow = self._create_workflow()

        logger.info("VisualizationAgent initialized")

    def _create_workflow(self) -> StateGraph:
        """
        Create LangGraph workflow for visualization generation.

        Workflow structure:
        - recommend_chart: Recommend best chart type
        - create_plotly_figure: Generate Plotly figure
        - apply_theme: Apply styling and branding
        - generate_insights: (Optional) Generate AI insights

        Returns:
            Compiled StateGraph
        """
        # Create workflow graph
        workflow = StateGraph(VisualizationState)

        # Define node functions with dependency injection
        async def _recommend_chart_with_deps(state: VisualizationState):
            return await recommend_chart_node(state, self.llm_client)

        async def _create_figure_with_deps(state: VisualizationState):
            return await create_plotly_figure_node(state, self.llm_client)

        async def _apply_theme_with_deps(state: VisualizationState):
            return await apply_theme_node(state)

        async def _generate_insights_with_deps(state: VisualizationState):
            return await generate_insights_node(state, self.llm_client)

        # Add nodes
        workflow.add_node("recommend_chart", _recommend_chart_with_deps)
        workflow.add_node("create_plotly_figure", _create_figure_with_deps)
        workflow.add_node("apply_theme", _apply_theme_with_deps)
        workflow.add_node("generate_insights", _generate_insights_with_deps)

        # Add edges
        workflow.add_edge(START, "recommend_chart")
        workflow.add_edge("recommend_chart", "create_plotly_figure")
        workflow.add_edge("create_plotly_figure", "apply_theme")

        # Conditional edge: insights or end?
        workflow.add_conditional_edges(
            "apply_theme",
            route_after_theme,
            {
                "generate_insights": "generate_insights",
                "end": END,
            }
        )
        workflow.add_edge("generate_insights", END)

        # Compile workflow with checkpointing
        checkpointer = MemorySaver()
        compiled_workflow = workflow.compile(checkpointer=checkpointer)

        logger.info("Visualization workflow compiled successfully")
        return compiled_workflow

    async def create_visualization(
        self,
        session_id: str,
        data: list,
        user_query: str,
        analysis_results: Optional[Dict[str, Any]] = None,
        chart_type: Optional[str] = None,
        plotly_theme: str = "plotly",
        custom_style_profile_id: Optional[str] = None,
        custom_style_profile: Optional[Dict[str, Any]] = None,
        style_overrides: Optional[Dict[str, Any]] = None,
        include_insights: bool = True,
    ) -> Dict[str, Any]:
        """
        Create visualization from data.

        Args:
            session_id: Analysis session ID
            data: Query results as list of dicts
            user_query: Original user query
            analysis_results: Optional analysis results from AnalysisAgent
            chart_type: Optional user-specified chart type (skip recommendation)
            plotly_theme: Base Plotly theme
            custom_style_profile_id: Optional custom style profile ID
            custom_style_profile: Optional loaded custom style profile
            style_overrides: Optional ad-hoc style customizations
            include_insights: Whether to generate insights

        Returns:
            Final state dictionary with:
            - visualization_id
            - plotly_figure (complete Plotly JSON)
            - chart_type
            - recommendation (if generated)
            - insights (if generated)
            - status
        """
        logger.info(f"Creating visualization for session {session_id}")

        try:
            # Generate unique visualization ID
            visualization_id = str(uuid4())

            # Create initial state
            initial_state = create_initial_visualization_state(
                visualization_id=visualization_id,
                session_id=session_id,
                user_query=user_query,
                data=data,
                analysis_results=analysis_results,
                chart_type=chart_type,
                plotly_theme=plotly_theme,
                custom_style_profile_id=custom_style_profile_id,
                options={
                    "include_insights": include_insights,
                    "style_overrides": style_overrides,
                }
            )

            # Add custom style profile if provided
            if custom_style_profile:
                initial_state["custom_style_profile"] = custom_style_profile

            # Configure for Langfuse tracing
            config = {
                "configurable": {
                    "thread_id": visualization_id,
                }
            }

            if self.langfuse_handler:
                config["callbacks"] = [self.langfuse_handler]

            # Execute workflow
            logger.info(f"[VisualizationAgent] Starting workflow for {visualization_id}")
            final_state = await self.workflow.ainvoke(initial_state, config=config)

            logger.info(
                f"[VisualizationAgent] Workflow completed: {final_state.get('workflow_status')}"
            )

            # Return final state as dict
            return dict(final_state)

        except Exception as e:
            logger.error(f"[VisualizationAgent] Failed: {e}")
            return {
                "visualization_id": visualization_id if 'visualization_id' in locals() else str(uuid4()),
                "session_id": session_id,
                "workflow_status": "failed",
                "errors": [f"Visualization creation failed: {str(e)}"],
                "chart_type": chart_type or "bar",
                "plotly_figure": None,
            }

    async def resume_visualization(
        self,
        visualization_id: str,
        updates: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Resume a visualization workflow from checkpoint.

        Useful for implementing human-in-the-loop or making adjustments.

        Args:
            visualization_id: Visualization ID (thread_id)
            updates: Optional state updates

        Returns:
            Updated final state
        """
        logger.info(f"Resuming visualization {visualization_id}")

        try:
            config = {
                "configurable": {
                    "thread_id": visualization_id,
                }
            }

            if self.langfuse_handler:
                config["callbacks"] = [self.langfuse_handler]

            # Resume from checkpoint
            final_state = await self.workflow.ainvoke(updates or {}, config=config)

            logger.info(f"[VisualizationAgent] Resume completed")
            return dict(final_state)

        except Exception as e:
            logger.error(f"[VisualizationAgent] Resume failed: {e}")
            raise


def create_visualization_agent(
    langfuse_handler: Optional[CallbackHandler] = None
) -> VisualizationAgent:
    """
    Factory function to create VisualizationAgent with dependencies.

    Args:
        langfuse_handler: Optional Langfuse callback handler

    Returns:
        Configured VisualizationAgent instance
    """
    # Create LLM client
    llm_client = LLMClient(
        api_key=settings.azure_openai.azure_openai_api_key,
        endpoint=settings.azure_openai.azure_openai_endpoint,
        deployment=settings.azure_openai.azure_openai_deployment,
        api_version=settings.azure_openai.azure_openai_api_version,
    )

    # Create agent
    agent = VisualizationAgent(
        llm_client=llm_client,
        langfuse_handler=langfuse_handler,
    )

    return agent
