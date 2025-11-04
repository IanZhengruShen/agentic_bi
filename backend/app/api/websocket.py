"""
WebSocket API endpoints for real-time workflow updates.

Provides WebSocket endpoint for establishing connections and receiving
real-time workflow progress updates.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.websocket.connection_manager import connection_manager
from app.websocket.events import create_workflow_event, WorkflowEventType
from app.core.security import decode_token
from app.services.auth_service import AuthService
from app.db.session import get_db
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_current_user_ws(token: str):
    """
    Authenticate WebSocket connection via JWT token.

    Args:
        token: JWT access token

    Returns:
        User object

    Raises:
        Exception: If authentication fails
    """
    from jose import JWTError, jwt
    from app.core.config import settings

    try:
        # Decode token manually to avoid HTTPException
        payload = jwt.decode(
            token,
            settings.jwt.jwt_secret,
            algorithms=[settings.jwt.jwt_algorithm]
        )
    except JWTError as e:
        raise Exception(f"Invalid token: {str(e)}")

    if payload.get("type") != "access":
        raise Exception("Invalid token type")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise Exception("Invalid token payload")

    # Get user from database
    async for db in get_db():
        auth_service = AuthService(db)
        user = await auth_service.get_user_by_id(uuid.UUID(user_id_str))

        if not user:
            raise Exception("User not found")

        return user


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),  # JWT token as query parameter
):
    """
    WebSocket endpoint for real-time workflow updates.

    **Connection**:
    ```javascript
    const ws = new WebSocket(`ws://localhost:8000/ws?token=${accessToken}`);
    ```

    **Subscription**:
    After connecting, subscribe to workflows:
    ```json
    {
        "action": "subscribe",
        "workflow_id": "workflow-123"
    }
    ```

    **Events Received**:
    - workflow.started
    - stage.started
    - stage.completed
    - agent.started
    - agent.completed
    - workflow.completed
    - workflow.failed

    **Heartbeat**:
    Send ping to keep connection alive:
    ```json
    {
        "action": "ping"
    }
    ```
    """
    logger.info(f"[WebSocket] New connection attempt with token: {token[:20]}...")

    # Authenticate user BEFORE accepting connection
    try:
        user = await get_current_user_ws(token)
        user_id = str(user.id)
        logger.info(f"[WebSocket] User {user_id} ({user.email}) authenticated successfully")
    except Exception as e:
        logger.error(f"[WebSocket] Authentication failed: {e}", exc_info=True)
        # Must accept connection before we can close it
        await websocket.accept()
        await websocket.close(code=1008, reason=f"Authentication failed: {str(e)}")
        return

    # Connect (this calls websocket.accept())
    await connection_manager.connect(websocket, user_id)

    # Send connection acknowledgment
    await websocket.send_json(
        create_workflow_event(
            WorkflowEventType.CONNECTION_ACK,
            workflow_id="system",
            message=f"Connected as user {user_id}",
        )
    )

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()

            action = data.get("action")

            if action == "subscribe":
                # Subscribe to workflow updates
                workflow_id = data.get("workflow_id")
                if workflow_id:
                    logger.info(
                        f"[WebSocket] User {user_id} subscribing to workflow_id={workflow_id}"
                    )
                    connection_manager.subscribe_to_workflow(websocket, workflow_id)

                    # Send subscription acknowledgment
                    await websocket.send_json(
                        create_workflow_event(
                            WorkflowEventType.SUBSCRIPTION_ACK,
                            workflow_id=workflow_id,
                            message=f"Subscribed to workflow {workflow_id}",
                        )
                    )
                else:
                    logger.warning(f"[WebSocket] Subscribe action missing workflow_id")

            elif action == "ping":
                # Heartbeat
                await websocket.send_json({"action": "pong"})

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"[WebSocket] Error: {e}", exc_info=True)
        connection_manager.disconnect(websocket, user_id)
