"""
Hybrid HITL Tools for LangGraph Workflows.

Combines LangGraph's interrupt() primitive with our custom notification
infrastructure for the best of both worlds:
- LangGraph handles state management and resumption
- Our service handles notifications, analytics, and audit trail

This is the RECOMMENDED approach for production LangGraph workflows.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from langchain_core.tools import tool
    from langgraph.types import interrupt
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    tool = None
    interrupt = None

from app.services.hitl_service import HITLService
from app.services.notification_service import get_notification_service, NotificationPreferences
from app.observability.hitl_tracing import trace_hitl_request, trace_hitl_response
from app.models.user import User

logger = logging.getLogger(__name__)


class HybridHITLTool:
    """
    Hybrid HITL tool that combines LangGraph's interrupt() with our infrastructure.

    Architecture:
    1. Uses LangGraph's interrupt() for workflow state management
    2. Uses our notification service for Slack/Email/WebSocket
    3. Uses our database for audit trail
    4. Uses Langfuse for analytics

    Benefits:
    - Simple integration (just add as a tool to your workflow)
    - Rich notifications (WebSocket, Slack, Email)
    - Full audit trail (PostgreSQL)
    - Analytics (Langfuse)
    - Elegant resumption (LangGraph's Command)
    """

    def __init__(
        self,
        hitl_service: Optional[HITLService] = None,
        enable_notifications: bool = True,
        enable_persistence: bool = True,
        enable_tracing: bool = True,
    ):
        """
        Initialize hybrid HITL tool.

        Args:
            hitl_service: Optional HITL service instance (with DB session)
            enable_notifications: Whether to send notifications
            enable_persistence: Whether to persist to database
            enable_tracing: Whether to trace in Langfuse
        """
        self.hitl_service = hitl_service
        self.notification_service = get_notification_service() if enable_notifications else None
        self.enable_persistence = enable_persistence
        self.enable_tracing = enable_tracing
        self.enable_notifications = enable_notifications

        logger.info(
            f"HybridHITLTool initialized "
            f"(notifications={enable_notifications}, "
            f"persistence={enable_persistence}, "
            f"tracing={enable_tracing})"
        )

    async def request_approval(
        self,
        query: str,
        intervention_type: str = "approval",
        workflow_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        options: Optional[List[Dict[str, Any]]] = None,
        timeout_seconds: int = 300,
        user: Optional[User] = None,
        notification_prefs: Optional[NotificationPreferences] = None,
    ) -> str:
        """
        Request human approval using hybrid approach.

        Flow:
        1. Persist request to database (if enabled)
        2. Send notifications via Slack/Email/WebSocket (if enabled)
        3. Trace in Langfuse (if enabled)
        4. Call interrupt() to pause LangGraph workflow
        5. Wait for Command with resume data
        6. Return response to workflow

        Args:
            query: Human-readable question for the human
            intervention_type: Type of intervention (e.g., "sql_approval", "data_access")
            workflow_id: Parent workflow identifier
            context: Additional context for decision
            options: Available options (if not provided, defaults to approve/reject)
            timeout_seconds: Timeout duration
            user: User who should respond (for notifications)
            notification_prefs: User's notification preferences

        Returns:
            Human response (approved, rejected, modified, etc.)

        Usage in LangGraph workflow:
        ```python
        @tool
        async def request_sql_approval(sql: str, workflow_id: str) -> str:
            '''Request approval for SQL query.'''
            hybrid_tool = HybridHITLTool(hitl_service)
            return await hybrid_tool.request_approval(
                query=f"Approve SQL query: {sql}",
                intervention_type="sql_approval",
                workflow_id=workflow_id,
                context={"sql": sql, "database": "production"},
                options=[
                    {"action": "approve", "label": "Approve", "description": "Execute query"},
                    {"action": "reject", "label": "Reject", "description": "Cancel query"},
                    {"action": "modify", "label": "Modify", "description": "Edit SQL first"},
                ],
            )
        ```
        """
        if not LANGGRAPH_AVAILABLE:
            raise RuntimeError("LangGraph not available - install langchain-core and langgraph")

        # Generate request ID
        import uuid
        request_id = str(uuid.uuid4())
        workflow_id = workflow_id or str(uuid.uuid4())

        # Default options if not provided
        if not options:
            options = [
                {"action": "approve", "label": "Approve", "description": "Approve and continue"},
                {"action": "reject", "label": "Reject", "description": "Reject and abort"},
            ]

        # Default context if not provided
        if not context:
            context = {"query": query}

        logger.info(
            f"[HybridHITL] Requesting {intervention_type} for workflow {workflow_id}: {query[:100]}"
        )

        # Step 1: Persist to database (if enabled)
        if self.enable_persistence and self.hitl_service:
            try:
                await self.hitl_service.repository.create_request(
                    workflow_id=workflow_id,
                    intervention_type=intervention_type,
                    context=context,
                    options=options,
                    timeout_seconds=timeout_seconds,
                    requester_user_id=str(user.id) if user else None,
                    company_id=str(user.company_id) if user else None,
                    required=True,
                )
                await self.hitl_service.db_session.commit()
                logger.info(f"[HybridHITL] Persisted request {request_id} to database")
            except Exception as e:
                logger.error(f"[HybridHITL] Failed to persist request: {e}")
                # Continue anyway - persistence is optional

        # Step 2: Trace in Langfuse (if enabled)
        if self.enable_tracing:
            try:
                trace_hitl_request(
                    request_id=request_id,
                    workflow_id=workflow_id,
                    intervention_type=intervention_type,
                    context=context,
                    options=options,
                    timeout_seconds=timeout_seconds,
                    required=True,
                )
                logger.info(f"[HybridHITL] Traced request {request_id} in Langfuse")
            except Exception as e:
                logger.error(f"[HybridHITL] Failed to trace request: {e}")

        # Step 3: Send notifications (if enabled)
        if self.enable_notifications and self.notification_service and user:
            try:
                notification_results = await self.notification_service.notify_intervention_required(
                    request_id=request_id,
                    workflow_id=workflow_id,
                    intervention_type=intervention_type,
                    context=context,
                    options=options,
                    timeout_seconds=timeout_seconds,
                    user_email=user.email,
                    user_preferences=notification_prefs,
                    dashboard_url=f"http://localhost:3000/workflows/{workflow_id}",  # TODO: Make configurable
                )
                logger.info(
                    f"[HybridHITL] Sent notifications for request {request_id}: {notification_results}"
                )
            except Exception as e:
                logger.error(f"[HybridHITL] Failed to send notifications: {e}")

        # Step 4: Use LangGraph's interrupt() to pause workflow
        # This is the magic - LangGraph handles state management!
        interrupt_data = {
            "request_id": request_id,
            "workflow_id": workflow_id,
            "intervention_type": intervention_type,
            "query": query,
            "context": context,
            "options": options,
            "timeout_seconds": timeout_seconds,
            "requested_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"[HybridHITL] Calling interrupt() for request {request_id}")

        # interrupt() pauses the workflow here
        # Workflow resumes when Command(resume=...) is provided
        human_response = interrupt(interrupt_data)

        # Step 5: Process response (workflow has resumed)
        response_action = human_response.get("action", "approve")
        response_feedback = human_response.get("feedback", "")
        response_data = human_response.get("data", {})

        logger.info(
            f"[HybridHITL] Received response for request {request_id}: {response_action}"
        )

        # Step 6: Persist response to database (if enabled)
        if self.enable_persistence and self.hitl_service:
            try:
                await self.hitl_service.repository.create_response(
                    request_id=request_id,
                    action=response_action,
                    data=response_data,
                    feedback=response_feedback,
                    responder_user_id=str(user.id) if user else None,
                    responder_name=user.full_name if user else None,
                    responder_email=user.email if user else None,
                )

                # Calculate response time
                requested_at = datetime.fromisoformat(interrupt_data["requested_at"])
                response_time_ms = int((datetime.utcnow() - requested_at).total_seconds() * 1000)

                # Update request status
                await self.hitl_service.repository.update_request_status(
                    request_id=request_id,
                    status=response_action,
                    responded_at=datetime.utcnow(),
                    response_time_ms=response_time_ms,
                )

                await self.hitl_service.db_session.commit()
                logger.info(f"[HybridHITL] Persisted response for request {request_id}")
            except Exception as e:
                logger.error(f"[HybridHITL] Failed to persist response: {e}")

        # Step 7: Trace response in Langfuse (if enabled)
        if self.enable_tracing:
            try:
                trace_hitl_response(
                    request_id=request_id,
                    workflow_id=workflow_id,
                    intervention_type=intervention_type,
                    action=response_action,
                    response_time_ms=response_time_ms if self.enable_persistence else 0,
                    responder_user_id=str(user.id) if user else None,
                    feedback=response_feedback,
                )
                logger.info(f"[HybridHITL] Traced response for request {request_id} in Langfuse")
            except Exception as e:
                logger.error(f"[HybridHITL] Failed to trace response: {e}")

        # Step 8: Return response to workflow
        if response_action == "approve":
            return f"Approved: {response_feedback}" if response_feedback else "Approved"
        elif response_action == "reject":
            return f"Rejected: {response_feedback}" if response_feedback else "Rejected"
        elif response_action == "modify":
            modified_data = response_data.get("modified_sql") or response_data.get("modified_query")
            return f"Modified: {modified_data}" if modified_data else "Modified"
        else:
            return f"{response_action}: {response_feedback}"


# Factory function for easy integration
def create_hybrid_hitl_tool(
    hitl_service: Optional[HITLService] = None,
    enable_notifications: bool = True,
    enable_persistence: bool = True,
    enable_tracing: bool = True,
) -> HybridHITLTool:
    """
    Factory function to create hybrid HITL tool.

    Args:
        hitl_service: Optional HITL service instance (with DB session)
        enable_notifications: Whether to send notifications
        enable_persistence: Whether to persist to database
        enable_tracing: Whether to trace in Langfuse

    Returns:
        HybridHITLTool instance

    Usage:
    ```python
    # In your workflow
    hybrid_hitl = create_hybrid_hitl_tool(
        hitl_service=get_hitl_service(db_session),
        enable_notifications=True,
        enable_persistence=True,
        enable_tracing=True,
    )

    # Use in any node
    response = await hybrid_hitl.request_approval(
        query="Approve this SQL query?",
        intervention_type="sql_approval",
        workflow_id=state.workflow_id,
        context={"sql": sql_query},
    )
    ```
    """
    return HybridHITLTool(
        hitl_service=hitl_service,
        enable_notifications=enable_notifications,
        enable_persistence=enable_persistence,
        enable_tracing=enable_tracing,
    )


# Example: LangGraph tool wrapper
if LANGGRAPH_AVAILABLE:
    @tool
    async def request_sql_approval(
        sql: str,
        database: str,
        workflow_id: str,
        hitl_service: Optional[HITLService] = None,
    ) -> str:
        """
        Request human approval for SQL query execution.

        This tool uses the hybrid HITL approach:
        - Pauses workflow with interrupt()
        - Sends Slack/Email notifications
        - Persists to database
        - Traces in Langfuse

        Args:
            sql: SQL query to approve
            database: Target database name
            workflow_id: Parent workflow identifier
            hitl_service: HITL service instance with DB session

        Returns:
            Approval decision (approved, rejected, modified)
        """
        hybrid_tool = create_hybrid_hitl_tool(hitl_service=hitl_service)

        response = await hybrid_tool.request_approval(
            query=f"Approve SQL query on {database}",
            intervention_type="sql_approval",
            workflow_id=workflow_id,
            context={
                "sql": sql,
                "database": database,
                "reason": "Requires human approval for data access",
            },
            options=[
                {
                    "action": "approve",
                    "label": "Approve",
                    "description": "Execute the SQL query as-is",
                },
                {
                    "action": "reject",
                    "label": "Reject",
                    "description": "Cancel the query and abort workflow",
                },
                {
                    "action": "modify",
                    "label": "Modify SQL",
                    "description": "Edit the SQL query before executing",
                },
            ],
            timeout_seconds=300,
        )

        return response
