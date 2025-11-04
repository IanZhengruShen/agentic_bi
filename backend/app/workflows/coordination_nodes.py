"""
Coordination nodes for unified multi-agent workflow.

These adapter nodes orchestrate multiple agents using LangGraph's subgraph pattern.
Each adapter node:
1. Transforms UnifiedWorkflowState → Agent-specific state
2. Invokes agent's compiled workflow (subgraph)
3. Transforms agent result → UnifiedWorkflowState updates

Key architectural principle: Use subgraph invocation (workflow.ainvoke),
NOT Python method calls, for true LangGraph orchestration.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.workflows.unified_state import UnifiedWorkflowState
from app.core.llm import LLMClient
from app.workflows.event_emitter import event_emitter
from app.services.hitl_service import HITLService

logger = logging.getLogger(__name__)


async def run_analysis_adapter_node(
    state: UnifiedWorkflowState,
    llm_client: LLMClient,
    mindsdb_service: Any = None,
    hitl_service: Any = None,
    langfuse_handler: Any = None,
) -> Dict[str, Any]:
    """
    Adapter node that invokes AnalysisAgent subgraph.

    This node demonstrates the LangGraph subgraph pattern:
    - Parent workflow (unified) invokes child workflow (AnalysisAgent)
    - State transformation happens in the adapter
    - Full Langfuse tracing across both workflows
    - Maintains agent independence (can still use standalone)

    Args:
        state: UnifiedWorkflowState from parent workflow
        llm_client: LLM client
        mindsdb_service: MindsDB service
        hitl_service: HITL service
        langfuse_handler: Langfuse callback handler

    Returns:
        State updates for UnifiedWorkflowState
    """
    logger.info(
        f"[UnifiedWorkflow:run_analysis] Invoking AnalysisAgent subgraph "
        f"for workflow {state.get('workflow_id', 'unknown')}"
    )

    # Emit stage started event
    await event_emitter.emit_stage_started(
        workflow_id=state["workflow_id"],
        stage="analysis",
        message="Analyzing query and generating SQL...",
        progress=0.1,
    )

    try:
        # Import AnalysisAgent and its state helper
        from app.agents.analysis_agent_langgraph import AnalysisAgentLangGraph
        from app.agents.workflow_state import create_initial_state

        # Create AnalysisAgent instance
        # Note: Fresh instance per invocation avoids stale state
        analysis_agent = AnalysisAgentLangGraph(
            llm_client=llm_client,
            mindsdb_service=mindsdb_service,
            hitl_service=hitl_service,
            langfuse_handler=langfuse_handler,
        )

        # Transform UnifiedWorkflowState → AnalysisAgent's WorkflowState input
        # IMPORTANT: Use create_initial_state to ensure all required fields are present
        # CRITICAL: Pass conversation_id for checkpointing and HITL workflow resume
        analysis_input = create_initial_state(
            session_id=state["workflow_id"],  # Reuse workflow_id as session_id
            query=state["user_query"],
            database=state["database"],
            conversation_id=state.get("conversation_id"),  # Critical for resume!
            user_id=state.get("user_id"),
            company_id=state.get("company_id"),
            options=state.get("options", {}),
        )

        # Configure Langfuse for subgraph
        # CRITICAL: Use SAME thread_id as parent so subgraph resumes from checkpoint
        conversation_id = state.get("conversation_id") or state["workflow_id"]

        config = {
            "configurable": {"thread_id": conversation_id}
        }
        if langfuse_handler:
            config["callbacks"] = [langfuse_handler]
            config["run_name"] = f"AnalysisAgent: {state['user_query'][:50]}"
            config["metadata"] = {
                "workflow_id": state["workflow_id"],
                "workflow_type": "unified",
                "agent": "analysis",
            }
            config["tags"] = ["unified-workflow", "analysis-agent"]

        # Emit agent started event
        await event_emitter.emit_agent_started(
            workflow_id=state["workflow_id"],
            agent="analysis",
            progress=0.15,
        )

        # CRITICAL: Check if subgraph has a paused state (from previous execution)
        # If so, we need to RESUME it, not start fresh
        from langgraph.types import Command

        snapshot = analysis_agent.workflow.get_state(config)
        if snapshot.next:
            # Subgraph is paused - check if we're resuming or starting
            logger.info(
                f"[UnifiedWorkflow:run_analysis] Found paused AnalysisAgent at node: {snapshot.next}"
            )
            # This shouldn't happen - if we're here, parent is resuming but subgraph is still paused
            # Re-raise to pause parent again
            from langgraph.errors import GraphInterrupt
            raise GraphInterrupt(
                f"AnalysisAgent still paused at node: {snapshot.next}"
            )

        # CRITICAL: Invoke AnalysisAgent's compiled workflow (subgraph)
        # This is the LangGraph subgraph pattern, not a Python method call
        logger.info(
            f"[UnifiedWorkflow:run_analysis] Executing AnalysisAgent.workflow.ainvoke()"
        )
        analysis_result = await analysis_agent.workflow.ainvoke(
            analysis_input,
            config=config
        )

        # CRITICAL: Check if subgraph is paused (waiting for human input)
        # When a subgraph calls interrupt(), it pauses but ainvoke() returns normally
        # We must check the state to see if there are pending nodes
        snapshot = analysis_agent.workflow.get_state(config)
        if snapshot.next:
            # Subgraph is paused - re-raise interrupt to pause parent workflow too
            logger.info(
                f"[UnifiedWorkflow:run_analysis] AnalysisAgent paused at node: {snapshot.next}"
            )

            # Re-raise GraphInterrupt to pause parent workflow
            from langgraph.errors import GraphInterrupt
            raise GraphInterrupt(
                f"AnalysisAgent paused for human input at node: {snapshot.next}"
            )

        # Emit agent completed event
        await event_emitter.emit_agent_completed(
            workflow_id=state["workflow_id"],
            agent="analysis",
            progress=0.35,
        )

        logger.info(
            f"[UnifiedWorkflow:run_analysis] AnalysisAgent completed: "
            f"status={analysis_result.get('workflow_status')}, "
            f"success={analysis_result.get('query_success')}"
        )

        # Transform AnalysisAgent output → UnifiedWorkflowState updates
        updates = {
            "workflow_status": "analyzed",
            "workflow_stage": "analyzed",
            "current_agent": "analysis",
            "analysis_session_id": state["workflow_id"],
            "schema": analysis_result.get("schema"),
            "generated_sql": analysis_result.get("generated_sql"),
            "sql_confidence": analysis_result.get("confidence"),
            "query_success": analysis_result.get("query_success", False),
            "query_data": analysis_result.get("query_data"),
            "analysis_results": analysis_result.get("analysis_results"),
            "enhanced_analysis": analysis_result.get("enhanced_analysis"),
            "insights": analysis_result.get("insights", []),
            "recommendations": analysis_result.get("recommendations", []),
            "agents_executed": ["analysis"],
        }

        # Accumulate any warnings or errors
        if analysis_result.get("warnings"):
            updates["warnings"] = analysis_result["warnings"]
        if analysis_result.get("errors"):
            updates["errors"] = analysis_result["errors"]

        return updates

    except Exception as e:
        logger.error(f"[UnifiedWorkflow:run_analysis] AnalysisAgent subgraph failed: {e}", exc_info=True)
        return {
            "errors": [f"Analysis failed: {str(e)}"],
            "workflow_status": "failed",
            "workflow_stage": "failed",
            "partial_success": False,
        }


async def decide_visualization_node(
    state: UnifiedWorkflowState,
    llm_client: LLMClient,
) -> Dict[str, Any]:
    """
    Decide if visualization should be created.

    Uses hybrid approach:
    1. Rule-based checks (fast filtering)
    2. LLM-based decision (intelligent analysis)

    This implements the "Routing" pattern from LangGraph:
    - Classifies the situation
    - Determines next step (visualize or skip)

    Args:
        state: UnifiedWorkflowState
        llm_client: LLM client for intelligent decision

    Returns:
        State updates with should_visualize flag
    """
    logger.info(
        f"[UnifiedWorkflow:decide_visualization] Evaluating visualization need "
        f"for workflow {state['workflow_id']}"
    )

    # Emit stage started event
    await event_emitter.emit_stage_started(
        workflow_id=state["workflow_id"],
        stage="deciding",
        message="Deciding if visualization is needed...",
        progress=0.4,
    )

    # === Rule-based checks (fast filtering) ===

    # Rule 1: If analysis failed, don't visualize
    if not state.get("query_success"):
        logger.info("[decide_visualization] Skipping: analysis query failed")
        return {
            "should_visualize": False,
            "skip_visualization_reason": "Analysis query failed",
            "workflow_stage": "deciding",
        }

    # Rule 2: If no data returned, don't visualize
    query_data = state.get("query_data")
    if not query_data or len(query_data) == 0:
        logger.info("[decide_visualization] Skipping: no data to visualize")
        return {
            "should_visualize": False,
            "skip_visualization_reason": "No data to visualize",
            "workflow_stage": "deciding",
        }

    # Rule 3: If user explicitly disabled auto-visualization
    if not state.get("options", {}).get("auto_visualize", True):
        logger.info("[decide_visualization] Skipping: auto-visualization disabled by user")
        return {
            "should_visualize": False,
            "skip_visualization_reason": "Auto-visualization disabled by user",
            "workflow_stage": "deciding",
        }

    # Rule 4: If only 1 row and 1 column (single scalar value), probably don't visualize
    if len(query_data) == 1 and len(query_data[0]) == 1:
        logger.info("[decide_visualization] Skipping: single scalar value")
        return {
            "should_visualize": False,
            "skip_visualization_reason": "Single scalar value - visualization not helpful",
            "workflow_stage": "deciding",
        }

    # === LLM-based decision (intelligent analysis) ===

    try:
        # Extract data characteristics
        row_count = len(query_data)
        columns = list(query_data[0].keys()) if query_data else []
        column_count = len(columns)

        # Build prompt for LLM
        prompt = f"""Analyze if a visualization would help answer the user's question.

User Query: "{state['user_query']}"

Data Characteristics:
- Rows: {row_count}
- Columns: {column_count}
- Column names: {', '.join(columns[:10])}{'...' if len(columns) > 10 else ''}

Analysis Summary: {state.get('analysis_results', {}).get('summary', 'N/A')}

Guidelines:
- Visualize if: trends, comparisons, distributions, patterns, or relationships would be clearer in a chart
- Visualize if: query contains keywords like "show", "compare", "trend", "over time", "by region", etc.
- Don't visualize if: simple data lookup, metadata query, single aggregation (e.g., "count of X")
- Don't visualize if: data is too sparse or unsuitable for charts

Respond with JSON only:
{{
    "should_visualize": true/false,
    "reasoning": "Brief explanation (1 sentence)",
    "suggested_chart_type": "bar/line/pie/scatter/heatmap/table or null"
}}
"""

        # Call LLM for decision
        logger.info("[decide_visualization] Calling LLM for intelligent decision")
        response = await llm_client.generate_text(
            prompt=prompt,
            system_prompt="You are a data visualization expert. Determine if a visualization would add value.",
            temperature=0.3,
            response_format="json_object",
        )

        # Parse LLM response
        import json
        decision = json.loads(response)

        should_visualize = decision.get("should_visualize", True)  # Default to True (bias toward visualizing)
        reasoning = decision.get("reasoning", "Visualization recommended")
        suggested_chart = decision.get("suggested_chart_type")

        logger.info(
            f"[decide_visualization] LLM decision: visualize={should_visualize}, "
            f"reason={reasoning}"
        )

        updates = {
            "should_visualize": should_visualize,
            "visualization_reasoning": reasoning,
            "workflow_stage": "deciding",
        }

        # Add suggested chart type if provided
        if suggested_chart and should_visualize:
            updates["recommended_chart_type"] = suggested_chart

        if not should_visualize:
            updates["skip_visualization_reason"] = reasoning

        return updates

    except Exception as e:
        # On LLM error, default to visualizing (bias toward creating viz)
        logger.warning(
            f"[decide_visualization] LLM decision failed: {e}. "
            f"Defaulting to visualize=True"
        )
        return {
            "should_visualize": True,
            "visualization_reasoning": "LLM decision unavailable, defaulting to visualize",
            "workflow_stage": "deciding",
            "warnings": [f"Visualization decision LLM failed: {str(e)}"],
        }


async def run_visualization_adapter_node(
    state: UnifiedWorkflowState,
    llm_client: LLMClient,
    langfuse_handler: Any = None,
) -> Dict[str, Any]:
    """
    Adapter node that invokes VisualizationAgent subgraph.

    Follows the same subgraph pattern as run_analysis_adapter_node:
    - Transform state
    - Invoke agent workflow (subgraph)
    - Transform results back

    Args:
        state: UnifiedWorkflowState from parent workflow
        llm_client: LLM client
        langfuse_handler: Langfuse callback handler

    Returns:
        State updates for UnifiedWorkflowState
    """
    logger.info(
        f"[UnifiedWorkflow:run_visualization] Invoking VisualizationAgent subgraph "
        f"for workflow {state['workflow_id']}"
    )

    # Emit stage started event
    await event_emitter.emit_stage_started(
        workflow_id=state["workflow_id"],
        stage="visualizing",
        message="Creating visualization...",
        progress=0.5,
    )

    try:
        # Import VisualizationAgent and its state helper
        from app.agents.visualization_agent import VisualizationAgent
        from app.agents.visualization_state import create_initial_visualization_state
        import uuid

        # Create VisualizationAgent instance
        viz_agent = VisualizationAgent(
            llm_client=llm_client,
            langfuse_handler=langfuse_handler,
        )

        # Generate unique visualization ID
        viz_id = str(uuid.uuid4())

        # Transform UnifiedWorkflowState → VisualizationAgent's VisualizationState input
        # IMPORTANT: Use create_initial_visualization_state to ensure all required fields
        visualization_input = create_initial_visualization_state(
            visualization_id=viz_id,
            session_id=state["analysis_session_id"],
            user_query=state["user_query"],
            data=state["query_data"],
            analysis_results=state.get("analysis_results"),
            # Allow user to override chart type
            chart_type=state.get("options", {}).get("chart_type") or state.get("recommended_chart_type"),
            plotly_theme=state.get("options", {}).get("plotly_theme", "plotly"),
            custom_style_profile_id=state.get("options", {}).get("custom_style_profile_id"),
            options={
                "include_insights": state.get("options", {}).get("include_insights", True),
            }
        )

        # Configure Langfuse for subgraph
        config = {
            "configurable": {"thread_id": viz_id}
        }
        if langfuse_handler:
            config["callbacks"] = [langfuse_handler]
            config["run_name"] = f"VisualizationAgent: {state['user_query'][:50]}"
            config["metadata"] = {
                "workflow_id": state["workflow_id"],
                "workflow_type": "unified",
                "agent": "visualization",
            }
            config["tags"] = ["unified-workflow", "visualization-agent"]

        # Emit agent started event
        await event_emitter.emit_agent_started(
            workflow_id=state["workflow_id"],
            agent="visualization",
            progress=0.55,
        )

        # CRITICAL: Invoke VisualizationAgent's compiled workflow (subgraph)
        logger.info(
            f"[UnifiedWorkflow:run_visualization] Executing VisualizationAgent.workflow.ainvoke()"
        )
        viz_result = await viz_agent.workflow.ainvoke(
            visualization_input,
            config=config
        )

        # Emit agent completed event
        await event_emitter.emit_agent_completed(
            workflow_id=state["workflow_id"],
            agent="visualization",
            progress=0.85,
        )

        logger.info(
            f"[UnifiedWorkflow:run_visualization] VisualizationAgent completed: "
            f"status={viz_result.get('workflow_status')}, "
            f"chart_type={viz_result.get('chart_type')}"
        )

        # Transform VisualizationAgent output → UnifiedWorkflowState updates
        updates = {
            "workflow_status": "visualized",
            "workflow_stage": "visualized",
            "current_agent": "visualization",
            "visualization_id": viz_id,
            "chart_type": viz_result.get("chart_type"),
            "plotly_figure": viz_result.get("plotly_figure"),
            "chart_insights": viz_result.get("chart_insights", []),
            "agents_executed": ["visualization"],
        }

        # Accumulate any warnings or errors
        if viz_result.get("warnings"):
            updates["warnings"] = viz_result["warnings"]
        if viz_result.get("errors"):
            updates["errors"] = viz_result["errors"]

        return updates

    except Exception as e:
        # Visualization failure is non-fatal - return partial success
        logger.error(
            f"[UnifiedWorkflow:run_visualization] VisualizationAgent subgraph failed: {e}",
            exc_info=True
        )
        return {
            "warnings": [f"Visualization failed: {str(e)}, returning analysis results only"],
            "partial_success": True,
            "workflow_stage": "visualized",
            # Don't set visualization_id on failure to indicate it didn't complete
        }


async def aggregate_results_node(
    state: UnifiedWorkflowState,
) -> Dict[str, Any]:
    """
    Aggregate results from all agents into final response.

    This node:
    - Combines insights from all executed agents
    - Calculates total execution time
    - Sets final workflow status
    - Prepares metadata for response

    Args:
        state: UnifiedWorkflowState

    Returns:
        Final state updates
    """
    logger.info(
        f"[UnifiedWorkflow:aggregate_results] Finalizing workflow {state['workflow_id']}"
    )

    # Emit finalizing stage event
    await event_emitter.emit_stage_started(
        workflow_id=state["workflow_id"],
        stage="finalizing",
        message="Finalizing results...",
        progress=0.9,
    )

    # Calculate total execution time
    created_at = datetime.fromisoformat(state["created_at"])
    completed_at = datetime.utcnow()
    execution_time_ms = int((completed_at - created_at).total_seconds() * 1000)

    # Aggregate all insights
    all_insights = list(state.get("insights", []))
    if state.get("chart_insights"):
        all_insights.extend(state["chart_insights"])

    # Determine final status
    has_errors = len(state.get("errors", [])) > 0
    partial_success = state.get("partial_success", False)

    if has_errors and not partial_success:
        final_status = "failed"
    elif partial_success:
        final_status = "partial_success"
    else:
        final_status = "completed"

    logger.info(
        f"[aggregate_results] Workflow {state['workflow_id']} completed: "
        f"status={final_status}, time={execution_time_ms}ms, "
        f"agents={state.get('agents_executed', [])}, "
        f"insights={len(all_insights)}"
    )

    # Emit workflow completion event (or failure event)
    if final_status == "failed":
        await event_emitter.emit_workflow_failed(
            workflow_id=state["workflow_id"],
            error=", ".join(state.get("errors", [])),
        )
    else:
        await event_emitter.emit_workflow_completed(
            workflow_id=state["workflow_id"],
            conversation_id=state.get("conversation_id"),
        )

    return {
        "workflow_status": final_status,
        "workflow_stage": "completed",
        "completed_at": completed_at.isoformat(),
        "execution_time_ms": execution_time_ms,
        "insights": all_insights,
    }


# ============================================
# Node: Human Review (HITL) - Parent Level
# ============================================


async def human_review_node(
    state: UnifiedWorkflowState,
    hitl_service: HITLService,
) -> Dict[str, Any]:
    """
    Node: Request human review for generated SQL using interrupt().

    This is at the PARENT workflow level (not in AnalysisAgent subgraph).
    This allows proper pause/resume without subgraph checkpoint conflicts.

    Args:
        state: Current unified workflow state
        hitl_service: HITL service instance

    Returns:
        State updates
    """
    from langgraph.types import interrupt

    logger.info("[Node: human_review] Requesting approval at parent workflow level...")

    # Create HITL request in database
    request_id = None
    timeout_seconds = 300

    try:
        from app.websocket.connection_manager import connection_manager
        from app.websocket.events import create_workflow_event, WorkflowEventType
        from datetime import timedelta

        # Persist HITL request to database first
        if hitl_service and hasattr(hitl_service, 'repository') and hitl_service.repository:
            db_request = await hitl_service.repository.create_request(
                workflow_id=state["workflow_id"],
                intervention_type="sql_review",
                context={
                    "generated_sql": state.get("generated_sql"),
                    "confidence": state.get("sql_confidence"),
                    "explanation": state.get("analysis_results", {}).get("explanation", ""),
                    "user_query": state.get("user_query", ""),
                },
                options=[
                    {"action": "approve", "label": "Execute as-is", "description": "Execute the generated SQL"},
                    {"action": "modify", "label": "Modify SQL", "description": "Provide modified SQL"},
                    {"action": "reject", "label": "Reject", "description": "Reject and stop"},
                ],
                timeout_seconds=timeout_seconds,
                conversation_id=state.get("conversation_id"),
                requester_user_id=state.get("user_id"),
                company_id=state.get("company_id"),
            )
            request_id = db_request.request_id

            # Commit immediately so frontend can find the request
            await hitl_service.db_session.commit()
            logger.info(f"[Node: human_review] Persisted HITL request: request_id={request_id}")

        # Broadcast WebSocket event
        timeout_at = datetime.utcnow() + timedelta(seconds=timeout_seconds)

        event = create_workflow_event(
            WorkflowEventType.HUMAN_INPUT_REQUIRED,
            workflow_id=state["workflow_id"],
            message=f"Human input required: approve_query",
            data={
                "request_id": request_id,
                "intervention_type": "sql_review",
                "context": {
                    "generated_sql": state.get("generated_sql"),
                    "confidence": state.get("sql_confidence"),
                    "user_query": state.get("user_query", ""),
                },
                "options": [
                    {"action": "approve", "label": "Execute as-is", "description": "Execute the generated SQL"},
                    {"action": "modify", "label": "Modify SQL", "description": "Provide modified SQL"},
                    {"action": "reject", "label": "Reject", "description": "Reject and stop"},
                ],
                "timeout_seconds": timeout_seconds,
                "timeout_at": timeout_at.isoformat(),
                "requested_at": datetime.utcnow().isoformat(),
            },
        )

        await connection_manager.broadcast_to_workflow(state["workflow_id"], event)
        logger.info(f"[Node: human_review] Broadcast WebSocket event: request_id={request_id}")

    except Exception as e:
        # Don't catch GraphInterrupt - let it propagate!
        if "Interrupt" in type(e).__name__ or "GraphInterrupt" in type(e).__name__:
            raise
        logger.error(f"[Node: human_review] Failed to create HITL request: {e}")

    # Pause workflow and wait for human input
    # On first execution: raises GraphInterrupt to pause
    # On resume: returns the human response value
    human_response = interrupt({
        "type": "human_review",
        "workflow_id": state["workflow_id"],
        "intervention_type": "approve_query",
        "context": {
            "generated_sql": state.get("generated_sql"),
            "confidence": state.get("sql_confidence"),
        },
        "options": [
            {"action": "approve", "label": "Execute as-is"},
            {"action": "modify", "label": "Modify SQL"},
            {"action": "reject", "label": "Reject"},
        ],
    })

    # When execution resumes, human_response contains the user's decision
    logger.info(f"[Node: human_review] Received response: {human_response.get('action')}")

    # Handle outcome
    updates = {
        "workflow_status": "reviewing",
    }

    if human_response.get("action") == "modify" and human_response.get("modified_sql"):
        updates["generated_sql"] = human_response["modified_sql"]

    elif human_response.get("action") == "reject":
        updates["workflow_status"] = "failed"
        updates["errors"] = ["Query rejected by user"]

    return updates


# === Routing Functions ===

def should_request_human_review(state: UnifiedWorkflowState) -> str:
    """
    Determine if human review is needed after analysis.

    Args:
        state: Current workflow state

    Returns:
        Next node name: "human_review" or "decide_visualization"
    """
    # Check if SQL confidence is below threshold (requiring review)
    sql_confidence = state.get("sql_confidence", 1.0)
    confidence_threshold = 0.7  # TODO: Make this configurable

    if sql_confidence < confidence_threshold:
        logger.info(f"SQL confidence {sql_confidence} < {confidence_threshold}, requesting human review")
        return "human_review"

    logger.info(f"SQL confidence {sql_confidence} >= {confidence_threshold}, skipping human review")
    return "decide_visualization"


def should_visualize_router(state: UnifiedWorkflowState) -> str:
    """
    Route after decide_visualization node.

    Returns:
        "visualize" if should create visualization, "skip" otherwise
    """
    if state.get("should_visualize", False):
        return "visualize"
    else:
        return "skip"
