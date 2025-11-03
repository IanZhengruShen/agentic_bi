"""
LangGraph-based Analysis Agent

This module implements the AnalysisAgent using LangGraph for:
- State-based workflow orchestration
- Conditional routing
- Built-in checkpointing
- Langfuse integration
- Human-in-the-loop support
"""

import logging
from typing import Optional, Dict, Any
from uuid import uuid4

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.agents.workflow_state import WorkflowState, create_initial_state
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


class AnalysisAgentLangGraph:
    """
    LangGraph-based Analysis Agent.

    Features:
    - State-based workflow with LangGraph
    - Conditional routing for HITL
    - Automatic state checkpointing
    - Langfuse tracing integration
    - Error recovery
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        mindsdb_service: Optional[MindsDBService] = None,
        hitl_service: Optional[HITLService] = None,
        langfuse_handler: Optional[CallbackHandler] = None,
        enable_checkpointing: bool = True,
    ):
        """
        Initialize LangGraph-based Analysis Agent.

        Args:
            llm_client: Optional LLM client
            mindsdb_service: Optional MindsDB service
            hitl_service: Optional HITL service
            langfuse_handler: Optional Langfuse handler
            enable_checkpointing: Whether to enable state checkpointing
        """
        self.llm_client = llm_client or create_llm_client(langfuse_handler=langfuse_handler)
        self.mindsdb_service = mindsdb_service or create_mindsdb_service()
        self.hitl_service = hitl_service or get_hitl_service()
        self.langfuse_handler = langfuse_handler

        # Create checkpointer if enabled
        self.checkpointer = MemorySaver() if enable_checkpointing else None

        # Build the workflow graph
        self.workflow = self._build_workflow()

        logger.info("LangGraph AnalysisAgent initialized")

    def _build_workflow(self) -> StateGraph:
        """
        Build the LangGraph workflow.

        Workflow structure:
        1. explore_schema -> 2. generate_sql
        3. [Conditional] human_review (if needs_review)
        4. validate_sql
        5. execute_query
        6. [Conditional] analyze_results (if successful)

        Returns:
            Compiled StateGraph
        """
        # Create graph with our state schema
        workflow = StateGraph(WorkflowState)

        # Add nodes with bound services
        workflow.add_node(
            "explore_schema",
            self._wrap_node(explore_schema_node, mindsdb_service=self.mindsdb_service)
        )

        workflow.add_node(
            "generate_sql",
            self._wrap_node(generate_sql_node, llm_client=self.llm_client)
        )

        workflow.add_node(
            "human_review",
            self._wrap_node(human_review_node, hitl_service=self.hitl_service)
        )

        workflow.add_node(
            "validate_sql",
            self._wrap_node(validate_sql_node, llm_client=self.llm_client)
        )

        workflow.add_node(
            "execute_query",
            self._wrap_node(execute_query_node, mindsdb_service=self.mindsdb_service)
        )

        workflow.add_node(
            "analyze_results",
            self._wrap_node(analyze_results_node)
        )

        # Define edges
        # Set entry point using START constant (LangGraph 1.0+ API)
        workflow.add_edge(START, "explore_schema")

        # explore_schema -> generate_sql
        workflow.add_edge("explore_schema", "generate_sql")

        # generate_sql -> [human_review OR validate_sql]
        workflow.add_conditional_edges(
            "generate_sql",
            should_request_human_review,
            {
                "human_review": "human_review",
                "validate_sql": "validate_sql",
            }
        )

        # human_review -> validate_sql (if approved/modified)
        workflow.add_edge("human_review", "validate_sql")

        # validate_sql -> execute_query
        workflow.add_conditional_edges(
            "validate_sql",
            should_proceed_after_validation,
            {
                "execute_query": "execute_query",
                "end": END,
            }
        )

        # execute_query -> [analyze_results OR END]
        workflow.add_conditional_edges(
            "execute_query",
            should_analyze_results,
            {
                "analyze_results": "analyze_results",
                "end": END,
            }
        )

        # analyze_results -> END
        workflow.add_edge("analyze_results", END)

        # Compile the graph
        compiled = workflow.compile(checkpointer=self.checkpointer)

        logger.info("LangGraph workflow compiled with nodes: " +
                   ", ".join(workflow.nodes.keys()))

        return compiled

    def _wrap_node(self, node_func, **kwargs):
        """
        Wrap node function to inject dependencies.

        Args:
            node_func: The node function to wrap
            **kwargs: Dependencies to inject

        Returns:
            Wrapped function
        """
        async def wrapped(state: WorkflowState) -> Dict[str, Any]:
            return await node_func(state, **kwargs)

        return wrapped

    async def execute(
        self,
        query: str,
        database: str,
        user_id: Optional[str] = None,
        company_id: Optional[str] = None,
        session_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> WorkflowState:
        """
        Execute the analysis workflow.

        Args:
            query: Natural language query
            database: Target database
            user_id: Optional user ID
            company_id: Optional company ID
            session_id: Optional session ID (for resuming)
            options: Optional configuration options

        Returns:
            Final workflow state
        """
        # Generate session ID if not provided
        session_id = session_id or str(uuid4())

        logger.info(f"Executing workflow for session {session_id}")

        # Create initial state
        initial_state = create_initial_state(
            session_id=session_id,
            query=query,
            database=database,
            user_id=user_id,
            company_id=company_id,
            options=options,
        )

        # Prepare config for Langfuse
        config = {
            "configurable": {"thread_id": session_id},
        }

        # Add Langfuse callback with custom metadata if available
        if self.langfuse_handler and LANGFUSE_AVAILABLE:
            # Create a new handler instance for this execution
            # The langfuse.langchain.CallbackHandler uses environment variables
            # and doesn't accept trace_name in __init__
            trace_handler = CallbackHandler()

            # Set metadata via the handler's internal client
            if hasattr(trace_handler, "trace") and trace_handler.trace is not None:
                # Update trace metadata
                trace_handler.trace.name = f"Analysis: {query[:50]}{'...' if len(query) > 50 else ''}"
                trace_handler.trace.user_id = user_id
                trace_handler.trace.session_id = session_id
                trace_handler.trace.metadata = {
                    "query": query,
                    "database": database,
                    "session_id": session_id,
                }
                trace_handler.trace.tags = ["analysis", "langgraph", database]

            config["callbacks"] = [trace_handler]
            config["run_name"] = f"Analysis: {query[:50]}{'...' if len(query) > 50 else ''}"
            config["metadata"] = {
                "query": query,
                "database": database,
                "session_id": session_id,
                "user_id": user_id,
            }
            config["tags"] = ["analysis", "langgraph", database]

        try:
            # Execute workflow
            final_state = await self.workflow.ainvoke(
                initial_state,
                config=config,
            )

            # Update trace with output if handler was created
            if "callbacks" in config and len(config["callbacks"]) > 0:
                trace_handler = config["callbacks"][0]
                # The handler will automatically capture the output through LangGraph
                # But we can explicitly add result metadata
                try:
                    # Access the Langfuse client to add final metadata
                    if hasattr(trace_handler, "langfuse") and final_state:
                        trace_handler.langfuse.trace(
                            output={
                                "success": final_state.get("query_success", False),
                                "row_count": final_state.get("row_count", 0),
                                "sql": final_state.get("generated_sql"),
                                "status": final_state.get("workflow_status"),
                            }
                        )
                except Exception as e:
                    logger.warning(f"Failed to update Langfuse trace output: {e}")

            logger.info(
                f"Workflow completed for session {session_id}: "
                f"status={final_state.get('workflow_status')}"
            )

            return final_state

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")

            # Return error state
            error_state = initial_state.copy()
            error_state["workflow_status"] = "failed"
            error_state["errors"] = [str(e)]

            return error_state

    async def resume(
        self,
        session_id: str,
        human_response: Optional[Dict[str, Any]] = None,
    ) -> WorkflowState:
        """
        Resume a paused workflow (e.g., after HITL response).

        This method uses LangGraph's Command pattern to resume from an interrupt().

        Args:
            session_id: Session ID to resume
            human_response: Human's response to the interrupt (e.g., {"action": "approve"})

        Returns:
            Final workflow state
        """
        from langgraph.types import Command

        logger.info(f"Resuming workflow for session {session_id}")

        if not self.checkpointer:
            raise ValueError("Cannot resume without checkpointing enabled")

        config = {
            "configurable": {"thread_id": session_id},
        }

        # Add Langfuse callback with custom metadata if available
        if self.langfuse_handler and LANGFUSE_AVAILABLE:
            # Get the current state to extract query info for the trace name
            current_state = self.get_state(session_id)
            query = current_state.get("query", "Resume") if current_state else "Resume"
            user_id = current_state.get("user_id") if current_state else None

            # Create a new handler instance for this execution
            trace_handler = CallbackHandler()

            # Set metadata via the handler's internal client
            if hasattr(trace_handler, "trace") and trace_handler.trace is not None:
                trace_handler.trace.name = f"Resume: {query[:50]}{'...' if len(query) > 50 else ''}"
                trace_handler.trace.user_id = user_id
                trace_handler.trace.session_id = session_id
                trace_handler.trace.metadata = {
                    "session_id": session_id,
                    "human_response": human_response,
                    "resumed": True,
                }
                trace_handler.trace.tags = ["analysis", "langgraph", "resume"]

            config["callbacks"] = [trace_handler]
            config["run_name"] = f"Resume: {query[:50]}{'...' if len(query) > 50 else ''}"
            config["metadata"] = {
                "session_id": session_id,
                "human_response": human_response,
                "resumed": True,
            }
            config["tags"] = ["analysis", "langgraph", "resume"]

        try:
            # Create Command with human response
            command = Command(resume=human_response) if human_response else None

            # Resume from checkpoint
            final_state = await self.workflow.ainvoke(
                command,  # Pass human response or None to continue
                config=config,
            )

            logger.info(f"Workflow resumed for session {session_id}")

            # Update trace with output if handler was created
            if "callbacks" in config and len(config["callbacks"]) > 0:
                trace_handler = config["callbacks"][0]
                try:
                    if hasattr(trace_handler, "langfuse") and final_state:
                        trace_handler.langfuse.trace(
                            output={
                                "success": final_state.get("query_success", False),
                                "row_count": final_state.get("row_count", 0),
                                "sql": final_state.get("generated_sql"),
                                "status": final_state.get("workflow_status"),
                            }
                        )
                except Exception as e:
                    logger.warning(f"Failed to update Langfuse trace output: {e}")

            return final_state

        except Exception as e:
            logger.error(f"Workflow resume failed: {e}")
            raise

    def get_state(self, session_id: str) -> Optional[WorkflowState]:
        """
        Get current state for a session.

        Args:
            session_id: Session ID

        Returns:
            Current state or None
        """
        if not self.checkpointer:
            return None

        config = {"configurable": {"thread_id": session_id}}

        try:
            snapshot = self.workflow.get_state(config)
            return snapshot.values if snapshot else None
        except Exception as e:
            logger.error(f"Failed to get state: {e}")
            return None

    async def stream(
        self,
        query: str,
        database: str,
        user_id: Optional[str] = None,
        company_id: Optional[str] = None,
        session_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        stream_mode: str = "updates",
    ):
        """
        Execute the analysis workflow with streaming for real-time updates.

        This method uses astream() to yield updates as the workflow progresses,
        enabling real-time WebSocket updates to the frontend.

        Args:
            query: Natural language query
            database: Target database
            user_id: Optional user ID
            company_id: Optional company ID
            session_id: Optional session ID (for resuming)
            options: Optional configuration options
            stream_mode: Streaming mode - "updates", "values", "debug"
                - "updates": Only node updates (recommended for WebSocket)
                - "values": Full state after each node
                - "debug": Detailed debugging info

        Yields:
            State updates or full state depending on stream_mode
        """
        from uuid import uuid4

        # Generate session ID if not provided
        session_id = session_id or str(uuid4())

        logger.info(f"Streaming workflow for session {session_id}")

        # Create initial state
        initial_state = create_initial_state(
            session_id=session_id,
            query=query,
            database=database,
            user_id=user_id,
            company_id=company_id,
            options=options,
        )

        # Prepare config for Langfuse
        config = {
            "configurable": {"thread_id": session_id},
        }

        # Add Langfuse callback with custom metadata if available
        if self.langfuse_handler and LANGFUSE_AVAILABLE:
            # Create a new handler instance for this execution
            trace_handler = CallbackHandler()

            # Set metadata via the handler's internal client
            if hasattr(trace_handler, "trace") and trace_handler.trace is not None:
                trace_handler.trace.name = f"Analysis Stream: {query[:50]}{'...' if len(query) > 50 else ''}"
                trace_handler.trace.user_id = user_id
                trace_handler.trace.session_id = session_id
                trace_handler.trace.metadata = {
                    "query": query,
                    "database": database,
                    "session_id": session_id,
                    "streaming": True,
                }
                trace_handler.trace.tags = ["analysis", "langgraph", "streaming", database]

            config["callbacks"] = [trace_handler]
            config["run_name"] = f"Analysis Stream: {query[:50]}{'...' if len(query) > 50 else ''}"
            config["metadata"] = {
                "query": query,
                "database": database,
                "session_id": session_id,
                "user_id": user_id,
                "streaming": True,
            }
            config["tags"] = ["analysis", "langgraph", "streaming", database]

        try:
            # Stream workflow execution
            final_event = None
            async for event in self.workflow.astream(
                initial_state,
                config=config,
                stream_mode=stream_mode,
            ):
                final_event = event
                yield event

            logger.info(f"Workflow streaming completed for session {session_id}")

            # Update trace with final output if handler was created
            if "callbacks" in config and len(config["callbacks"]) > 0 and final_event:
                trace_handler = config["callbacks"][0]
                try:
                    # Extract final state from last event
                    if isinstance(final_event, dict) and "__end__" in final_event:
                        final_state = final_event["__end__"]
                        if hasattr(trace_handler, "langfuse") and final_state:
                            trace_handler.langfuse.trace(
                                output={
                                    "success": final_state.get("query_success", False),
                                    "row_count": final_state.get("row_count", 0),
                                    "sql": final_state.get("generated_sql"),
                                    "status": final_state.get("workflow_status"),
                                }
                            )
                except Exception as e:
                    logger.warning(f"Failed to update Langfuse trace output: {e}")

        except Exception as e:
            logger.error(f"Workflow streaming failed: {e}")
            # Yield error event
            yield {
                "error": str(e),
                "session_id": session_id,
                "workflow_status": "failed",
            }

    async def resume_stream(
        self,
        session_id: str,
        human_response: Optional[Dict[str, Any]] = None,
        stream_mode: str = "updates",
    ):
        """
        Resume a paused workflow with streaming.

        Args:
            session_id: Session ID to resume
            human_response: Human's response to the interrupt
            stream_mode: Streaming mode

        Yields:
            State updates as workflow resumes
        """
        from langgraph.types import Command

        logger.info(f"Resuming workflow with streaming for session {session_id}")

        if not self.checkpointer:
            raise ValueError("Cannot resume without checkpointing enabled")

        config = {
            "configurable": {"thread_id": session_id},
        }

        if self.langfuse_handler:
            config["callbacks"] = [self.langfuse_handler]

        try:
            # Create Command with human response
            command = Command(resume=human_response) if human_response else None

            # Stream workflow resumption
            async for event in self.workflow.astream(
                command,
                config=config,
                stream_mode=stream_mode,
            ):
                yield event

            logger.info(f"Workflow resume streaming completed for session {session_id}")

        except Exception as e:
            logger.error(f"Workflow resume streaming failed: {e}")
            yield {
                "error": str(e),
                "session_id": session_id,
                "workflow_status": "failed",
            }

    async def cleanup(self):
        """Cleanup agent resources."""
        if self.mindsdb_service:
            await self.mindsdb_service.close()
        logger.info("AnalysisAgent cleaned up")

    def visualize(self, output_path: str = "workflow_graph.png"):
        """
        Visualize the workflow graph (requires graphviz).

        Args:
            output_path: Path to save visualization
        """
        try:
            from IPython.display import Image, display

            display(Image(self.workflow.get_graph().draw_mermaid_png()))
        except Exception as e:
            logger.warning(f"Could not visualize workflow: {e}")


# Factory function
def create_analysis_agent(
    langfuse_handler: Optional[CallbackHandler] = None,
    enable_checkpointing: bool = True,
) -> AnalysisAgentLangGraph:
    """
    Factory function to create LangGraph-based Analysis Agent.

    Args:
        langfuse_handler: Optional Langfuse callback handler
        enable_checkpointing: Whether to enable state persistence

    Returns:
        Configured AnalysisAgentLangGraph instance
    """
    return AnalysisAgentLangGraph(
        langfuse_handler=langfuse_handler,
        enable_checkpointing=enable_checkpointing,
    )
