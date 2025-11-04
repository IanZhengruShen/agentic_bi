"""
Unit tests for WebSocket ConnectionManager.

Tests connection lifecycle, subscription management, and event broadcasting.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.websocket.connection_manager import ConnectionManager


class TestConnectionManager:
    """Test suite for ConnectionManager."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ConnectionManager for each test."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket connection."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect_new_user(self, manager, mock_websocket):
        """Test connecting a new user."""
        user_id = "user-123"

        await manager.connect(mock_websocket, user_id)

        # Verify WebSocket was accepted
        mock_websocket.accept.assert_called_once()

        # Verify user was registered
        assert user_id in manager.active_connections
        assert mock_websocket in manager.active_connections[user_id]

    @pytest.mark.asyncio
    async def test_connect_multiple_connections_same_user(
        self, manager, mock_websocket
    ):
        """Test multiple connections for the same user."""
        user_id = "user-123"
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()

        await manager.connect(mock_websocket, user_id)
        await manager.connect(ws2, user_id)

        # Verify both connections are tracked
        assert len(manager.active_connections[user_id]) == 2
        assert mock_websocket in manager.active_connections[user_id]
        assert ws2 in manager.active_connections[user_id]

    def test_disconnect_user(self, manager, mock_websocket):
        """Test disconnecting a user."""
        user_id = "user-123"
        manager.active_connections[user_id] = {mock_websocket}

        manager.disconnect(mock_websocket, user_id)

        # Verify user was removed
        assert user_id not in manager.active_connections

    def test_disconnect_one_of_multiple_connections(self, manager, mock_websocket):
        """Test disconnecting one connection when user has multiple."""
        user_id = "user-123"
        ws2 = AsyncMock()
        manager.active_connections[user_id] = {mock_websocket, ws2}

        manager.disconnect(mock_websocket, user_id)

        # Verify only the disconnected socket was removed
        assert user_id in manager.active_connections
        assert mock_websocket not in manager.active_connections[user_id]
        assert ws2 in manager.active_connections[user_id]

    def test_disconnect_from_workflow_subscriptions(self, manager, mock_websocket):
        """Test that disconnect removes WebSocket from workflow subscriptions."""
        user_id = "user-123"
        workflow_id = "workflow-456"

        manager.active_connections[user_id] = {mock_websocket}
        manager.workflow_subscriptions[workflow_id] = {mock_websocket}

        manager.disconnect(mock_websocket, user_id)

        # Verify workflow subscription was cleaned up
        assert workflow_id not in manager.workflow_subscriptions

    def test_subscribe_to_workflow(self, manager, mock_websocket):
        """Test subscribing a WebSocket to a workflow."""
        workflow_id = "workflow-123"

        manager.subscribe_to_workflow(mock_websocket, workflow_id)

        # Verify subscription was registered
        assert workflow_id in manager.workflow_subscriptions
        assert mock_websocket in manager.workflow_subscriptions[workflow_id]

    def test_subscribe_multiple_clients_to_workflow(self, manager, mock_websocket):
        """Test multiple clients subscribing to the same workflow."""
        workflow_id = "workflow-123"
        ws2 = AsyncMock()

        manager.subscribe_to_workflow(mock_websocket, workflow_id)
        manager.subscribe_to_workflow(ws2, workflow_id)

        # Verify both are subscribed
        assert len(manager.workflow_subscriptions[workflow_id]) == 2
        assert mock_websocket in manager.workflow_subscriptions[workflow_id]
        assert ws2 in manager.workflow_subscriptions[workflow_id]

    @pytest.mark.asyncio
    async def test_broadcast_to_workflow(self, manager, mock_websocket):
        """Test broadcasting a message to workflow subscribers."""
        workflow_id = "workflow-123"
        message = {"event": "test", "data": "hello"}

        manager.workflow_subscriptions[workflow_id] = {mock_websocket}

        await manager.broadcast_to_workflow(workflow_id, message)

        # Verify message was sent
        mock_websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_to_workflow_no_subscribers(self, manager):
        """Test broadcasting to a workflow with no subscribers."""
        workflow_id = "workflow-123"
        message = {"event": "test"}

        # Should not raise an error
        await manager.broadcast_to_workflow(workflow_id, message)

    @pytest.mark.asyncio
    async def test_broadcast_to_workflow_handles_send_failure(
        self, manager, mock_websocket
    ):
        """Test that broadcast handles WebSocket send failures gracefully."""
        workflow_id = "workflow-123"
        message = {"event": "test"}

        # Simulate send failure
        mock_websocket.send_json = AsyncMock(side_effect=Exception("Send failed"))
        manager.workflow_subscriptions[workflow_id] = {mock_websocket}

        await manager.broadcast_to_workflow(workflow_id, message)

        # Verify failed connection was removed
        assert mock_websocket not in manager.workflow_subscriptions[workflow_id]

    @pytest.mark.asyncio
    async def test_broadcast_to_user(self, manager, mock_websocket):
        """Test broadcasting a message to all connections for a user."""
        user_id = "user-123"
        message = {"event": "test", "data": "hello"}

        manager.active_connections[user_id] = {mock_websocket}

        await manager.broadcast_to_user(user_id, message)

        # Verify message was sent
        mock_websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_to_user_multiple_connections(self, manager, mock_websocket):
        """Test broadcasting to user with multiple connections."""
        user_id = "user-123"
        ws2 = AsyncMock()
        ws2.send_json = AsyncMock()
        message = {"event": "test"}

        manager.active_connections[user_id] = {mock_websocket, ws2}

        await manager.broadcast_to_user(user_id, message)

        # Verify message was sent to both connections
        mock_websocket.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_to_user_no_connections(self, manager):
        """Test broadcasting to a user with no active connections."""
        user_id = "user-123"
        message = {"event": "test"}

        # Should not raise an error
        await manager.broadcast_to_user(user_id, message)

    @pytest.mark.asyncio
    async def test_broadcast_to_user_handles_send_failure(
        self, manager, mock_websocket
    ):
        """Test that broadcast handles send failures when notifying users."""
        user_id = "user-123"
        message = {"event": "test"}

        # Simulate send failure
        mock_websocket.send_json = AsyncMock(side_effect=Exception("Send failed"))
        manager.active_connections[user_id] = {mock_websocket}

        await manager.broadcast_to_user(user_id, message)

        # Verify failed connection was removed
        assert mock_websocket not in manager.active_connections[user_id]
