"""
Unified Workflow Orchestrator for Multi-Agent Coordination.

This module implements the core orchestration engine that coordinates
multiple agents (AnalysisAgent, VisualizationAgent) using LangGraph.

Key architectural principle: SUBGRAPH PATTERN
- Parent workflow (this orchestrator) contains adapter nodes
- Each adapter node invokes an agent's compiled workflow (subgraph)
- State transformation happens in adapters
- Single unified Langfuse trace across all agents
- Agents remain independent and reusable
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.workflows.unified_state import UnifiedWorkflowState
from app.workflows.coordination_nodes import (
    run_analysis_adapter_node,
    decide_visualization_node,
    run_visualization_adapter_node,
    aggregate_results_node,
    human_review_node,
    should_visualize_router,
    should_request_human_review,
)
from app.workflows.event_emitter import event_emitter
from app.core.llm import LLMClient, create_llm_client
from app.services.mindsdb_service import MindsDBService, create_mindsdb_service
from app.services.hitl_service import HITLService, get_hitl_service

try:
    from langfuse.langchain import CallbackHandler
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    CallbackHandler = None

logger = logging.getLogger(__name__)


class UnifiedWorkflowOrchestrator:
    """
    Orchestrates multi-agent workflows using LangGraph.

    Architecture:
    - Unified workflow graph (parent graph)
    - AnalysisAgent workflow (subgraph 1)
    - VisualizationAgent workflow (subgraph 2)
    - Adapter nodes transform state between graphs

    Workflow Pattern: PROMPT CHAINING + ROUTING
    1. run_analysis_adapter → invokes AnalysisAgent subgraph
    2. decide_visualization → determines if visualization needed (routing)
    3. run_visualization_adapter → (conditional) invokes VisualizationAgent subgraph
    4. aggregate_results → combines results from all agents

    Key Benefits:
    - One API call produces complete results (analysis + visualization)
    - Intelligent routing (only visualize when appropriate)
    - Error recovery (partial success mode)
    - Unified Langfuse traces
    - Agents remain independent
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        mindsdb_service: Optional[MindsDBService] = None,
        hitl_service: Optional[HITLService] = None,
        langfuse_handler: Optional[CallbackHandler] = None,
    ):
        """
        Initialize unified workflow orchestrator.

        Note: Agents are NOT stored as instance variables.
        They are created fresh in adapter nodes to avoid stale state.

        Args:
            llm_client: LLM client for all agents
            mindsdb_service: MindsDB service for AnalysisAgent
            hitl_service: HITL service for human intervention
            langfuse_handler: Langfuse callback handler for tracing
        """
        self.llm_client = llm_client or create_llm_client(langfuse_handler=langfuse_handler)
        self.mindsdb_service = mindsdb_service or create_mindsdb_service()
        self.hitl_service = hitl_service or get_hitl_service()
        self.langfuse_handler = langfuse_handler

        # Build unified workflow
        self.workflow = self._create_unified_workflow()

        logger.info("UnifiedWorkflowOrchestrator initialized")

    def _create_unified_workflow(self):
        """
        Create unified workflow graph using subgraph pattern.

        Workflow Structure (Prompt Chaining + Routing + HITL):

        START
          ↓
        run_analysis_adapter (invokes AnalysisAgent subgraph)
          ↓
        [CONDITIONAL EDGE: Check SQL confidence]
          ├─ Low confidence → human_review (HITL pause/resume)
          │                      ↓
          └─ High confidence → decide_visualization
                               ↓
        decide_visualization (routing: LLM + rules decide if viz needed)
          ↓
        [CONDITIONAL EDGE]
          ├─ "visualize" → run_visualization_adapter (invokes VisualizationAgent subgraph)
          └─ "skip" → aggregate_results
          ↓
        aggregate_results (combines insights, calculates time)
          ↓
        END

        Each adapter node:
        1. Transforms UnifiedWorkflowState → Agent-specific state
        2. Invokes agent.workflow.ainvoke() (subgraph invocation)
        3. Transforms agent result → UnifiedWorkflowState updates

        Returns:
            Compiled LangGraph workflow
        """
        logger.info("[Orchestrator] Building unified workflow graph")

        # Create state graph
        workflow = StateGraph(UnifiedWorkflowState)

        # Define adapter nodes with dependency injection
        # These nodes invoke agent subgraphs, not Python methods

        async def _run_analysis_with_deps(state: UnifiedWorkflowState):
            """Adapter node: invoke AnalysisAgent subgraph"""
            return await run_analysis_adapter_node(
                state,
                llm_client=self.llm_client,
                mindsdb_service=self.mindsdb_service,
                hitl_service=self.hitl_service,
                langfuse_handler=self.langfuse_handler,
            )

        async def _decide_visualization_with_deps(state: UnifiedWorkflowState):
            """Decision node: determine if visualization needed"""
            return await decide_visualization_node(
                state,
                llm_client=self.llm_client,
            )

        async def _run_visualization_with_deps(state: UnifiedWorkflowState):
            """Adapter node: invoke VisualizationAgent subgraph"""
            return await run_visualization_adapter_node(
                state,
                llm_client=self.llm_client,
                langfuse_handler=self.langfuse_handler,
            )

        async def _aggregate_results_with_deps(state: UnifiedWorkflowState):
            """Aggregation node: combine results from all agents"""
            return await aggregate_results_node(state)

        async def _human_review_with_deps(state: UnifiedWorkflowState):
            """HITL node: request human review for low-confidence SQL"""
            return await human_review_node(
                state,
                hitl_service=self.hitl_service,
            )

        # Add nodes to graph
        workflow.add_node("run_analysis", _run_analysis_with_deps)
        workflow.add_node("human_review", _human_review_with_deps)
        workflow.add_node("decide_visualization", _decide_visualization_with_deps)
        workflow.add_node("run_visualization", _run_visualization_with_deps)
        workflow.add_node("aggregate_results", _aggregate_results_with_deps)

        # Define edges: Prompt Chaining + HITL
        workflow.add_edge(START, "run_analysis")

        # Conditional edge: Check if human review needed based on SQL confidence
        workflow.add_conditional_edges(
            "run_analysis",
            should_request_human_review,
            {
                "human_review": "human_review",
                "decide_visualization": "decide_visualization",
            }
        )

        # After human review, continue to visualization decision
        workflow.add_edge("human_review", "decide_visualization")

        # Conditional edge: Routing pattern
        # Route based on should_visualize flag
        workflow.add_conditional_edges(
            "decide_visualization",
            should_visualize_router,
            {
                "visualize": "run_visualization",
                "skip": "aggregate_results",
            }
        )

        # Visualization → Aggregation
        workflow.add_edge("run_visualization", "aggregate_results")

        # Aggregation → END
        workflow.add_edge("aggregate_results", END)

        # Compile workflow with checkpointing
        checkpointer = MemorySaver()
        compiled_workflow = workflow.compile(checkpointer=checkpointer)

        logger.info(
            "[Orchestrator] Unified workflow compiled with nodes: "
            "run_analysis, decide_visualization, run_visualization, aggregate_results"
        )

        return compiled_workflow

    async def execute(
        self,
        user_query: str,
        database: str,
        user_id: str,
        company_id: str,
        workflow_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute unified workflow: Query → Analysis → Visualization (optional).

        This method orchestrates the complete flow:
        1. Creates initial UnifiedWorkflowState
        2. Invokes compiled unified workflow
        3. Workflow automatically invokes agent subgraphs via adapters
        4. Returns complete results (analysis + visualization if applicable)

        Args:
            user_query: Natural language query
            database: Target database
            user_id: User ID for auth and tracing
            company_id: Company ID for multi-tenancy
            workflow_id: Optional workflow ID. If provided, uses this ID instead of generating one.
                        Allows client to subscribe to WebSocket events before execution.
            conversation_id: Optional conversation thread ID for memory.
                           If provided, workflow loads previous conversation context.
                           If None, creates new conversation.
            options: Optional workflow options:
                - auto_visualize: bool (default True) - automatically create viz
                - chart_type: str - force specific chart type
                - plotly_theme: str - Plotly theme (default "plotly")
                - custom_style_profile_id: str - custom style profile ID
                - include_insights: bool (default True) - generate insights
                - limit_rows: int (default 1000) - query result limit

        Returns:
            Complete workflow results:
            {
                "workflow_id": str,
                "workflow_status": "completed" | "partial_success" | "failed",

                # Analysis results
                "generated_sql": str,
                "query_data": List[Dict],
                "analysis_results": Dict,
                "enhanced_analysis": Dict,

                # Visualization results (if created)
                "visualization_id": str,
                "chart_type": str,
                "plotly_figure": Dict,

                # Combined insights
                "insights": List[str],
                "recommendations": List[str],

                # Metadata
                "execution_time_ms": int,
                "agents_executed": List[str],
                "created_at": str,
                "completed_at": str,
            }

        Raises:
            Exception: If workflow execution fails catastrophically
        """
        # Use provided workflow_id or generate a new one
        workflow_id_provided = workflow_id is not None
        if workflow_id is None:
            workflow_id = str(uuid.uuid4())

        # Use provided conversation_id or create new one
        # This is the KEY for conversation memory - reuse same ID for follow-ups!
        conversation_id = conversation_id or str(uuid.uuid4())

        logger.info(
            f"[Orchestrator] Executing workflow_id={workflow_id} "
            f"(client_provided={workflow_id_provided}) "
            f"in conversation {conversation_id}: "
            f"query='{user_query}', database='{database}'"
        )

        # Create initial state for unified workflow
        initial_state = {
            # Request
            "workflow_id": workflow_id,
            "conversation_id": conversation_id,
            "user_query": user_query,
            "database": database,
            "options": options or {},

            # User context
            "user_id": user_id,
            "company_id": company_id,

            # Workflow control
            "workflow_status": "pending",
            "workflow_stage": "init",
            "current_agent": None,

            # Analysis state (will be populated by AnalysisAgent)
            "analysis_session_id": None,
            "schema": None,
            "generated_sql": None,
            "sql_confidence": None,
            "query_success": False,
            "query_data": None,
            "analysis_results": None,
            "enhanced_analysis": None,

            # Visualization decision (will be set by decide_visualization)
            "should_visualize": False,
            "visualization_reasoning": None,
            "skip_visualization_reason": None,

            # Visualization state (will be populated by VisualizationAgent if visualized)
            "visualization_id": None,
            "recommended_chart_type": None,
            "chart_type": None,
            "plotly_figure": None,
            "chart_insights": [],

            # Aggregated results
            "insights": [],
            "recommendations": [],

            # Error handling
            "errors": [],
            "warnings": [],
            "partial_success": False,

            # Metadata
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "execution_time_ms": None,
            "agents_executed": [],
        }

        # Configure Langfuse for unified workflow
        # CRITICAL: Use conversation_id as thread_id for checkpointer!
        # This enables conversation memory - same ID = same conversation context
        config = {
            "configurable": {"thread_id": conversation_id}
        }

        if self.langfuse_handler and LANGFUSE_AVAILABLE:
            # Create handler for this execution
            trace_handler = CallbackHandler()

            config["callbacks"] = [trace_handler]
            config["run_name"] = f"Unified: {user_query[:50]}{'...' if len(user_query) > 50 else ''}"
            config["metadata"] = {
                "workflow_id": workflow_id,
                "conversation_id": conversation_id,
                "workflow_type": "unified",
                "query": user_query,
                "database": database,
                "user_id": user_id,
                "company_id": company_id,
            }
            config["tags"] = ["unified-workflow", "multi-agent", database]

        try:
            # Emit workflow started event
            await event_emitter.emit_workflow_started(
                workflow_id=workflow_id,
                conversation_id=conversation_id,
                user_query=user_query,
            )

            # Execute unified workflow
            # This will automatically invoke agent subgraphs as it executes
            logger.info(f"[Orchestrator] Invoking workflow.ainvoke() for {workflow_id}")

            final_state = await self.workflow.ainvoke(initial_state, config=config)

            # CRITICAL: Check if workflow is paused (waiting for human input)
            # When interrupt() is called, ainvoke() returns normally but workflow is paused
            # We must check the state to see if there are pending nodes
            snapshot = self.workflow.get_state(config)
            if snapshot.next:
                # Workflow is paused - there are pending nodes
                logger.info(
                    f"[Orchestrator] Workflow {workflow_id} paused at node: {snapshot.next}"
                )

                # Emit workflow.paused event
                try:
                    from app.websocket.connection_manager import connection_manager
                    from app.websocket.events import create_workflow_event, WorkflowEventType

                    event = create_workflow_event(
                        WorkflowEventType.WORKFLOW_PAUSED,
                        workflow_id=workflow_id,
                        message=f"Workflow paused for human input",
                    )
                    await connection_manager.broadcast_to_workflow(workflow_id, event)
                except Exception as broadcast_error:
                    logger.error(f"Failed to broadcast pause event: {broadcast_error}")

                # Return paused state
                return {
                    "workflow_id": workflow_id,
                    "conversation_id": conversation_id,
                    "workflow_status": "paused",
                    "message": "Workflow paused - waiting for human input",
                    "pause_reason": "human_input_required",
                    "next_node": snapshot.next[0] if snapshot.next else None,
                    "created_at": initial_state["created_at"],
                    "paused_at": datetime.utcnow().isoformat(),
                    "agents_executed": final_state.get("agents_executed", []),
                }

            # Workflow completed normally
            logger.info(
                f"[Orchestrator] Workflow {workflow_id} completed: "
                f"status={final_state.get('workflow_status')}, "
                f"time={final_state.get('execution_time_ms')}ms, "
                f"agents={final_state.get('agents_executed', [])}"
            )

            # Return final state as dict
            return dict(final_state)

        except Exception as e:
            # Check if this is a LangGraph interrupt (HITL pause)
            if "Interrupt" in str(type(e).__name__):
                logger.info(
                    f"[Orchestrator] Workflow {workflow_id} paused for human input (interrupt detected)"
                )

                # Emit workflow.paused event
                try:
                    from app.websocket.connection_manager import connection_manager
                    from app.websocket.events import create_workflow_event, WorkflowEventType

                    event = create_workflow_event(
                        WorkflowEventType.WORKFLOW_PAUSED,
                        workflow_id=workflow_id,
                        message="Workflow paused for human review",
                    )
                    await connection_manager.broadcast_to_workflow(workflow_id, event)
                except Exception as broadcast_error:
                    logger.error(f"Failed to broadcast pause event: {broadcast_error}")

                # Return paused state (not an error!)
                return {
                    "workflow_id": workflow_id,
                    "conversation_id": conversation_id,
                    "workflow_status": "paused",
                    "message": "Workflow paused - waiting for human input",
                    "pause_reason": "human_review_required",
                    "created_at": initial_state["created_at"],
                    "paused_at": datetime.utcnow().isoformat(),
                    "agents_executed": initial_state.get("agents_executed", []),
                }

            # For other exceptions, treat as actual failure
            logger.error(
                f"[Orchestrator] Workflow {workflow_id} failed catastrophically: {e}",
                exc_info=True
            )

            # Emit workflow.failed event
            try:
                from app.websocket.connection_manager import connection_manager
                from app.websocket.events import create_workflow_event, WorkflowEventType

                event = create_workflow_event(
                    WorkflowEventType.WORKFLOW_FAILED,
                    workflow_id=workflow_id,
                    message=f"Workflow failed: {str(e)}",
                    error=str(e),
                )
                await connection_manager.broadcast_to_workflow(workflow_id, event)
            except Exception as broadcast_error:
                logger.error(f"Failed to broadcast failure event: {broadcast_error}")

            # Return error state
            return {
                "workflow_id": workflow_id,
                "conversation_id": conversation_id,
                "workflow_status": "failed",
                "errors": [f"Workflow execution failed: {str(e)}"],
                "created_at": initial_state["created_at"],
                "completed_at": datetime.utcnow().isoformat(),
                "execution_time_ms": int(
                    (datetime.utcnow() - datetime.fromisoformat(initial_state["created_at"])).total_seconds() * 1000
                ),
                "agents_executed": [],
            }

    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get workflow status from checkpoint.

        Args:
            workflow_id: Workflow ID (thread_id)

        Returns:
            Workflow state if found, None otherwise
        """
        # Note: MemorySaver checkpoints are in-memory only
        # For production, use persistent checkpointer (e.g., PostgreSQL)
        logger.info(f"[Orchestrator] Getting status for workflow {workflow_id}")

        # LangGraph checkpoint retrieval (if using persistent checkpointer)
        # For MemorySaver, checkpoints are lost after process restart
        # This is a placeholder for future enhancement

        return None


# Global orchestrator instance for workflow resumption
_global_orchestrator = None


async def resume_workflow(
    thread_id: str,
    resume_value: Dict[str, Any],
    workflow_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Resume a paused workflow with user's response.

    Args:
        thread_id: Thread ID for checkpointer (usually conversation_id)
        resume_value: User's response data
        workflow_id: Original workflow ID (for WebSocket broadcasting)

    Returns:
        Final workflow state after resumption
    """
    global _global_orchestrator

    if not _global_orchestrator:
        logger.error("[Resume] No global orchestrator available - cannot resume")
        raise RuntimeError("Orchestrator not initialized")

    logger.info(f"[Resume] Resuming workflow thread {thread_id} with: {resume_value}")

    try:
        from langgraph.types import Command

        # Resume the workflow using Command
        # Use the same thread_id that was used during initial execution
        config = {"configurable": {"thread_id": thread_id}}

        # Create Command to resume with user's response
        command = Command(resume=resume_value)

        # Invoke workflow with resume command
        final_state = await _global_orchestrator.workflow.ainvoke(command, config=config)

        logger.info(f"[Resume] Workflow thread {thread_id} resumed and completed")

        # Emit workflow.resumed and workflow.completed events
        from app.websocket.connection_manager import connection_manager
        from app.websocket.events import create_workflow_event, WorkflowEventType

        # Use explicitly provided workflow_id or get from final state
        broadcast_id = workflow_id or final_state.get("workflow_id", thread_id)

        # Resumed event
        event_resumed = create_workflow_event(
            WorkflowEventType.WORKFLOW_RESUMED,
            workflow_id=broadcast_id,
            message="Workflow resumed after human review",
        )
        await connection_manager.broadcast_to_workflow(broadcast_id, event_resumed)

        # Completed event
        event_completed = create_workflow_event(
            WorkflowEventType.WORKFLOW_COMPLETED,
            workflow_id=broadcast_id,
            message="Workflow completed successfully",
        )
        await connection_manager.broadcast_to_workflow(broadcast_id, event_completed)

        return dict(final_state)

    except Exception as e:
        logger.error(f"[Resume] Failed to resume workflow thread {thread_id}: {e}", exc_info=True)
        raise


def create_unified_orchestrator(
    llm_client: Optional[LLMClient] = None,
    mindsdb_service: Optional[MindsDBService] = None,
    hitl_service: Optional[HITLService] = None,
    langfuse_handler: Optional[CallbackHandler] = None,
) -> UnifiedWorkflowOrchestrator:
    """
    Factory function to create UnifiedWorkflowOrchestrator.

    Args:
        llm_client: Optional LLM client
        mindsdb_service: Optional MindsDB service
        hitl_service: Optional HITL service
        langfuse_handler: Optional Langfuse handler

    Returns:
        UnifiedWorkflowOrchestrator instance
    """
    global _global_orchestrator

    orchestrator = UnifiedWorkflowOrchestrator(
        llm_client=llm_client,
        mindsdb_service=mindsdb_service,
        hitl_service=hitl_service,
        langfuse_handler=langfuse_handler,
    )

    # Store globally for workflow resumption
    _global_orchestrator = orchestrator

    return orchestrator
