"""
WebSocket connection manager for real-time workflow updates.

Manages WebSocket connections, subscriptions, and event broadcasting.
"""

from typing import Dict, Set
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time workflow updates.

    Features:
    - Multiple connections per user
    - Connection lifecycle management
    - Event broadcasting with filtering
    - Automatic cleanup of stale connections
    """

    def __init__(self):
        # user_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}

        # workflow_id -> Set[WebSocket] (for targeted broadcasting)
        self.workflow_subscriptions: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: WebSocket connection
            user_id: User ID for connection tracking
        """
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)

        logger.info(
            f"[WebSocket] User {user_id} connected. "
            f"Total connections: {len(self.active_connections[user_id])}"
        )

    def disconnect(self, websocket: WebSocket, user_id: str):
        """
        Remove a WebSocket connection.

        Args:
            websocket: WebSocket to disconnect
            user_id: User ID
        """
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)

            # Cleanup empty sets
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        # Remove from workflow subscriptions
        for workflow_id in list(self.workflow_subscriptions.keys()):
            self.workflow_subscriptions[workflow_id].discard(websocket)
            if not self.workflow_subscriptions[workflow_id]:
                del self.workflow_subscriptions[workflow_id]

        logger.info(f"[WebSocket] User {user_id} disconnected")

    def subscribe_to_workflow(self, websocket: WebSocket, workflow_id: str):
        """
        Subscribe a connection to workflow updates.

        Args:
            websocket: WebSocket connection
            workflow_id: Workflow to subscribe to
        """
        if workflow_id not in self.workflow_subscriptions:
            self.workflow_subscriptions[workflow_id] = set()

        self.workflow_subscriptions[workflow_id].add(websocket)

        logger.info(
            f"[WebSocket] Client subscribed to workflow {workflow_id}. "
            f"Total subscribers: {len(self.workflow_subscriptions[workflow_id])}"
        )

    async def broadcast_to_workflow(self, workflow_id: str, message: dict):
        """
        Broadcast message to all clients subscribed to a workflow.

        Args:
            workflow_id: Target workflow
            message: Message to broadcast
        """
        if workflow_id not in self.workflow_subscriptions:
            logger.warning(
                f"[ConnectionManager] No subscribers for workflow_id={workflow_id}. "
                f"Event type={message.get('event_type')} will be dropped."
            )
            return

        subscriber_count = len(self.workflow_subscriptions[workflow_id])
        logger.info(
            f"[ConnectionManager] Broadcasting {message.get('event_type')} "
            f"to {subscriber_count} subscriber(s) for workflow_id={workflow_id}"
        )

        disconnected = []

        for websocket in self.workflow_subscriptions[workflow_id]:
            try:
                await websocket.send_json(message)
                logger.debug(f"[ConnectionManager] Successfully sent event to subscriber")
            except Exception as e:
                logger.error(f"[WebSocket] Failed to send to client: {e}")
                disconnected.append(websocket)

        # Cleanup failed connections
        for ws in disconnected:
            self.workflow_subscriptions[workflow_id].discard(ws)

    async def broadcast_to_user(self, user_id: str, message: dict):
        """
        Broadcast message to all connections for a user.

        Args:
            user_id: Target user
            message: Message to broadcast
        """
        if user_id not in self.active_connections:
            return

        disconnected = []

        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"[WebSocket] Failed to send to user {user_id}: {e}")
                disconnected.append(websocket)

        # Cleanup failed connections
        for ws in disconnected:
            self.active_connections[user_id].discard(ws)


# Singleton instance
connection_manager = ConnectionManager()
