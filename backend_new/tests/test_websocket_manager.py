import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.websocket_manager import WebSocketManager
from app.schemas import WebSocketEvent
import asyncio


@pytest.mark.asyncio
async def test_connect_and_broadcast():
    """Test connecting a WebSocket and broadcasting an event."""
    manager = WebSocketManager()

    # Mock WebSocket
    ws = MagicMock()
    ws.send_json = AsyncMock()

    # Connect
    manager.connect("exec_123", ws)
    assert "exec_123" in manager.connections
    assert ws in manager.connections["exec_123"]

    # Broadcast event
    event = WebSocketEvent.create(
        event_type="test_event",
        execution_id="exec_123",
        data={"message": "test"}
    )
    await manager.broadcast("exec_123", event)

    # Verify send_json was called
    ws.send_json.assert_called_once()
    call_args = ws.send_json.call_args[0][0]
    assert call_args["event_type"] == "test_event"

    # Clean up ping task
    if "exec_123" in manager.ping_tasks:
        manager.ping_tasks["exec_123"].cancel()


@pytest.mark.asyncio
async def test_disconnect():
    """Test disconnecting a WebSocket."""
    manager = WebSocketManager()
    ws = MagicMock()
    ws.send_json = AsyncMock()

    manager.connect("exec_123", ws)
    manager.disconnect("exec_123", ws)

    assert ws not in manager.connections.get("exec_123", [])
    # Verify ping task was cancelled
    assert "exec_123" not in manager.ping_tasks


@pytest.mark.asyncio
async def test_websocket_ping_keep_alive():
    """Test that WebSocket ping keep-alive mechanism is started on connect."""
    manager = WebSocketManager()
    ws = MagicMock()
    ws.send_json = AsyncMock()

    # Connect
    manager.connect("exec_123", ws)

    # Verify ping task was created
    assert "exec_123" in manager.ping_tasks
    assert isinstance(manager.ping_tasks["exec_123"], asyncio.Task)

    # Clean up
    manager.disconnect("exec_123", ws)


@pytest.mark.asyncio
async def test_websocket_ping_enforcement():
    """Test that WebSocket ping interval is enforced (30 seconds constraint)."""
    manager = WebSocketManager()
    ws = MagicMock()
    ws.send_json = AsyncMock()

    # Verify ping interval is set from config (30 seconds)
    assert manager.ping_interval == 30

    # Clean up
    if "exec_123" in manager.ping_tasks:
        manager.ping_tasks["exec_123"].cancel()
