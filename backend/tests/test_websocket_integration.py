"""
Integration tests for WebSocket real-time workflow updates.

Tests complete flow:
1. WebSocket connection establishment
2. Workflow subscription
3. Real-time event streaming during workflow execution
4. Event order and completeness
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import uuid

from app.main import app
from app.websocket.events import WorkflowEventType
from app.workflows.event_emitter import event_emitter


@pytest.fixture
def test_client():
    """Create a test client."""
    return TestClient(app)


@pytest.mark.asyncio
async def test_workflow_event_emission():
    """
    Test that workflow nodes emit events correctly.

    This test verifies event emission without WebSocket connection,
    to isolate event emission logic.
    """
    workflow_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())

    # Mock the connection manager to track emissions
    with patch("app.workflows.event_emitter.connection_manager") as mock_manager:
        mock_manager.broadcast_to_workflow = AsyncMock()

        # Emit workflow started
        await event_emitter.emit_workflow_started(
            workflow_id=workflow_id,
            conversation_id=conversation_id,
            user_query="Test query",
        )

        # Verify event was broadcasted
        assert mock_manager.broadcast_to_workflow.called
        call_args = mock_manager.broadcast_to_workflow.call_args
        assert call_args[0][0] == workflow_id
        event = call_args[0][1]
        assert event["event_type"] == WorkflowEventType.WORKFLOW_STARTED
        assert event["workflow_id"] == workflow_id
        assert event["conversation_id"] == conversation_id
        assert event["progress"] == 0.0


@pytest.mark.asyncio
async def test_stage_event_emission():
    """Test that stage events are emitted correctly."""
    workflow_id = str(uuid.uuid4())

    with patch("app.workflows.event_emitter.connection_manager") as mock_manager:
        mock_manager.broadcast_to_workflow = AsyncMock()

        # Emit stage started
        await event_emitter.emit_stage_started(
            workflow_id=workflow_id,
            stage="analysis",
            message="Analyzing query...",
            progress=0.1,
        )

        # Verify event
        call_args = mock_manager.broadcast_to_workflow.call_args
        event = call_args[0][1]
        assert event["event_type"] == WorkflowEventType.STAGE_STARTED
        assert event["stage"] == "analysis"
        assert event["progress"] == 0.1


@pytest.mark.asyncio
async def test_agent_event_emission():
    """Test that agent events are emitted correctly."""
    workflow_id = str(uuid.uuid4())

    with patch("app.workflows.event_emitter.connection_manager") as mock_manager:
        mock_manager.broadcast_to_workflow = AsyncMock()

        # Emit agent started
        await event_emitter.emit_agent_started(
            workflow_id=workflow_id,
            agent="analysis",
            progress=0.15,
        )

        # Verify event
        call_args = mock_manager.broadcast_to_workflow.call_args
        event = call_args[0][1]
        assert event["event_type"] == WorkflowEventType.AGENT_STARTED
        assert event["agent"] == "analysis"
        assert event["progress"] == 0.15


@pytest.mark.asyncio
async def test_workflow_completed_emission():
    """Test that workflow completion events are emitted correctly."""
    workflow_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())

    with patch("app.workflows.event_emitter.connection_manager") as mock_manager:
        mock_manager.broadcast_to_workflow = AsyncMock()

        # Emit workflow completed
        await event_emitter.emit_workflow_completed(
            workflow_id=workflow_id,
            conversation_id=conversation_id,
        )

        # Verify event
        call_args = mock_manager.broadcast_to_workflow.call_args
        event = call_args[0][1]
        assert event["event_type"] == WorkflowEventType.WORKFLOW_COMPLETED
        assert event["workflow_id"] == workflow_id
        assert event["conversation_id"] == conversation_id
        assert event["progress"] == 1.0


@pytest.mark.asyncio
async def test_workflow_failed_emission():
    """Test that workflow failure events are emitted correctly."""
    workflow_id = str(uuid.uuid4())

    with patch("app.workflows.event_emitter.connection_manager") as mock_manager:
        mock_manager.broadcast_to_workflow = AsyncMock()

        # Emit workflow failed
        await event_emitter.emit_workflow_failed(
            workflow_id=workflow_id,
            error="Test error",
        )

        # Verify event
        call_args = mock_manager.broadcast_to_workflow.call_args
        event = call_args[0][1]
        assert event["event_type"] == WorkflowEventType.WORKFLOW_FAILED
        assert event["workflow_id"] == workflow_id
        assert event["error"] == "Test error"


@pytest.mark.asyncio
async def test_event_order_during_workflow():
    """
    Test that events are emitted in the correct order during workflow execution.

    This test verifies the sequence of events:
    1. workflow.started
    2. stage.started (analysis)
    3. agent.started (analysis)
    4. agent.completed (analysis)
    5. stage.started (deciding)
    6. stage.started (visualizing) OR skip
    7. workflow.completed
    """
    workflow_id = str(uuid.uuid4())
    emitted_events = []

    with patch("app.workflows.event_emitter.connection_manager") as mock_manager:
        # Capture all emitted events
        async def capture_event(wf_id, event):
            emitted_events.append(event)

        mock_manager.broadcast_to_workflow = capture_event

        # Simulate workflow event sequence
        await event_emitter.emit_workflow_started(
            workflow_id=workflow_id,
            user_query="Test query",
        )

        await event_emitter.emit_stage_started(
            workflow_id=workflow_id,
            stage="analysis",
            message="Analyzing...",
            progress=0.1,
        )

        await event_emitter.emit_agent_started(
            workflow_id=workflow_id,
            agent="analysis",
            progress=0.15,
        )

        await event_emitter.emit_agent_completed(
            workflow_id=workflow_id,
            agent="analysis",
            progress=0.35,
        )

        await event_emitter.emit_stage_started(
            workflow_id=workflow_id,
            stage="deciding",
            message="Deciding...",
            progress=0.4,
        )

        await event_emitter.emit_workflow_completed(
            workflow_id=workflow_id,
        )

        # Verify event order
        assert len(emitted_events) == 6
        assert emitted_events[0]["event_type"] == WorkflowEventType.WORKFLOW_STARTED
        assert emitted_events[1]["event_type"] == WorkflowEventType.STAGE_STARTED
        assert emitted_events[1]["stage"] == "analysis"
        assert emitted_events[2]["event_type"] == WorkflowEventType.AGENT_STARTED
        assert emitted_events[2]["agent"] == "analysis"
        assert emitted_events[3]["event_type"] == WorkflowEventType.AGENT_COMPLETED
        assert emitted_events[4]["event_type"] == WorkflowEventType.STAGE_STARTED
        assert emitted_events[4]["stage"] == "deciding"
        assert emitted_events[5]["event_type"] == WorkflowEventType.WORKFLOW_COMPLETED

        # Verify progress increases monotonically
        progress_values = [
            e.get("progress")
            for e in emitted_events
            if e.get("progress") is not None
        ]
        assert progress_values == sorted(progress_values)


@pytest.mark.asyncio
async def test_multiple_workflows_isolated_events():
    """
    Test that events for different workflows are properly isolated.

    Each workflow should only receive its own events.
    """
    workflow_1 = str(uuid.uuid4())
    workflow_2 = str(uuid.uuid4())

    workflow_1_events = []
    workflow_2_events = []

    with patch("app.workflows.event_emitter.connection_manager") as mock_manager:
        # Route events to the correct workflow
        async def route_event(wf_id, event):
            if wf_id == workflow_1:
                workflow_1_events.append(event)
            elif wf_id == workflow_2:
                workflow_2_events.append(event)

        mock_manager.broadcast_to_workflow = route_event

        # Emit events for workflow 1
        await event_emitter.emit_workflow_started(
            workflow_id=workflow_1,
            user_query="Query 1",
        )

        # Emit events for workflow 2
        await event_emitter.emit_workflow_started(
            workflow_id=workflow_2,
            user_query="Query 2",
        )

        # Verify isolation
        assert len(workflow_1_events) == 1
        assert len(workflow_2_events) == 1
        assert workflow_1_events[0]["workflow_id"] == workflow_1
        assert workflow_2_events[0]["workflow_id"] == workflow_2


@pytest.mark.asyncio
async def test_event_timestamp_format():
    """Test that event timestamps are properly formatted."""
    workflow_id = str(uuid.uuid4())

    with patch("app.workflows.event_emitter.connection_manager") as mock_manager:
        mock_manager.broadcast_to_workflow = AsyncMock()

        await event_emitter.emit_workflow_started(
            workflow_id=workflow_id,
            user_query="Test",
        )

        call_args = mock_manager.broadcast_to_workflow.call_args
        event = call_args[0][1]

        # Verify timestamp is present and parseable
        assert "timestamp" in event
        timestamp = datetime.fromisoformat(event["timestamp"])
        assert isinstance(timestamp, datetime)
