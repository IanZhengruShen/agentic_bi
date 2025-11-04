"""
Workflow event emitter for real-time progress updates.

Emits workflow events to WebSocket clients during workflow execution.
"""

import asyncio
from typing import Optional
from app.websocket.connection_manager import connection_manager
from app.websocket.events import create_workflow_event, WorkflowEventType
import logging

logger = logging.getLogger(__name__)


class WorkflowEventEmitter:
    """
    Emits workflow events to WebSocket clients.

    Integrated into workflow nodes to provide real-time progress updates.
    """

    @staticmethod
    async def emit_workflow_started(
        workflow_id: str,
        conversation_id: Optional[str] = None,
        user_query: Optional[str] = None,
    ):
        """Emit workflow started event."""
        logger.info(f"[EventEmitter] Emitting workflow.started for workflow_id={workflow_id}")
        await connection_manager.broadcast_to_workflow(
            workflow_id,
            create_workflow_event(
                WorkflowEventType.WORKFLOW_STARTED,
                workflow_id=workflow_id,
                conversation_id=conversation_id,
                message=f"Processing: {user_query[:50] if user_query else 'query'}",
                progress=0.0,
            ),
        )

    @staticmethod
    async def emit_stage_started(
        workflow_id: str,
        stage: str,
        message: str,
        progress: float,
    ):
        """Emit stage started event."""
        logger.info(f"[EventEmitter] Emitting stage.started (stage={stage}) for workflow_id={workflow_id}")
        await connection_manager.broadcast_to_workflow(
            workflow_id,
            create_workflow_event(
                WorkflowEventType.STAGE_STARTED,
                workflow_id=workflow_id,
                stage=stage,
                message=message,
                progress=progress,
            ),
        )

    @staticmethod
    async def emit_stage_completed(
        workflow_id: str,
        stage: str,
        message: str,
        progress: float,
    ):
        """Emit stage completed event."""
        await connection_manager.broadcast_to_workflow(
            workflow_id,
            create_workflow_event(
                WorkflowEventType.STAGE_COMPLETED,
                workflow_id=workflow_id,
                stage=stage,
                message=message,
                progress=progress,
            ),
        )

    @staticmethod
    async def emit_agent_started(
        workflow_id: str,
        agent: str,
        progress: float,
    ):
        """Emit agent started event."""
        await connection_manager.broadcast_to_workflow(
            workflow_id,
            create_workflow_event(
                WorkflowEventType.AGENT_STARTED,
                workflow_id=workflow_id,
                agent=agent,
                message=f"{agent.capitalize()} agent processing...",
                progress=progress,
            ),
        )

    @staticmethod
    async def emit_agent_completed(
        workflow_id: str,
        agent: str,
        progress: float,
    ):
        """Emit agent completed event."""
        await connection_manager.broadcast_to_workflow(
            workflow_id,
            create_workflow_event(
                WorkflowEventType.AGENT_COMPLETED,
                workflow_id=workflow_id,
                agent=agent,
                message=f"{agent.capitalize()} agent completed",
                progress=progress,
            ),
        )

    @staticmethod
    async def emit_workflow_completed(
        workflow_id: str,
        conversation_id: Optional[str] = None,
    ):
        """Emit workflow completed event."""
        await connection_manager.broadcast_to_workflow(
            workflow_id,
            create_workflow_event(
                WorkflowEventType.WORKFLOW_COMPLETED,
                workflow_id=workflow_id,
                conversation_id=conversation_id,
                message="Workflow completed successfully",
                progress=1.0,
            ),
        )

    @staticmethod
    async def emit_workflow_failed(
        workflow_id: str,
        error: str,
    ):
        """Emit workflow failed event."""
        await connection_manager.broadcast_to_workflow(
            workflow_id,
            create_workflow_event(
                WorkflowEventType.WORKFLOW_FAILED,
                workflow_id=workflow_id,
                error=error,
                message=f"Workflow failed: {error}",
                progress=0.0,
            ),
        )


# Singleton instance
event_emitter = WorkflowEventEmitter()
