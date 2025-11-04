"""
WebSocket event types and schemas for workflow updates.

Defines event types and message formats for real-time communication.
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class WorkflowEventType(str, Enum):
    """Types of workflow events."""

    # Lifecycle events
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    WORKFLOW_PAUSED = "workflow.paused"
    WORKFLOW_RESUMED = "workflow.resumed"

    # Stage events
    STAGE_STARTED = "stage.started"
    STAGE_COMPLETED = "stage.completed"
    STAGE_FAILED = "stage.failed"

    # Progress events
    PROGRESS_UPDATE = "progress.update"

    # Agent events
    AGENT_STARTED = "agent.started"
    AGENT_COMPLETED = "agent.completed"

    # HITL events
    HUMAN_INPUT_REQUIRED = "human_input.required"
    HUMAN_INPUT_RECEIVED = "human_input.received"
    HUMAN_INPUT_TIMEOUT = "human_input.timeout"

    # Connection events
    CONNECTION_ACK = "connection.ack"
    SUBSCRIPTION_ACK = "subscription.ack"


class WorkflowEvent(BaseModel):
    """
    Workflow event message.

    Sent to clients via WebSocket.
    """

    event_type: WorkflowEventType
    workflow_id: str
    conversation_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    # Event-specific data
    stage: Optional[str] = None  # analysis, deciding, visualizing, finalizing
    agent: Optional[str] = None  # analysis, visualization
    progress: Optional[float] = None  # 0.0 - 1.0
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    # Error information (if failed)
    error: Optional[str] = None


def create_workflow_event(
    event_type: WorkflowEventType, workflow_id: str, **kwargs
) -> Dict[str, Any]:
    """
    Create a workflow event message.

    Args:
        event_type: Type of event
        workflow_id: Workflow ID
        **kwargs: Additional event data

    Returns:
        Event dictionary ready for JSON serialization
    """
    event = WorkflowEvent(event_type=event_type, workflow_id=workflow_id, **kwargs)
    return event.model_dump()
