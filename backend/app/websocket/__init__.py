"""
WebSocket module for real-time workflow updates.

This module provides:
- WebSocket connection management
- Real-time event streaming
- Workflow progress updates
- Client subscription management
"""

from app.websocket.connection_manager import ConnectionManager, connection_manager
from app.websocket.events import (
    WorkflowEvent,
    WorkflowEventType,
    create_workflow_event,
)

__all__ = [
    "ConnectionManager",
    "connection_manager",
    "WorkflowEvent",
    "WorkflowEventType",
    "create_workflow_event",
]
