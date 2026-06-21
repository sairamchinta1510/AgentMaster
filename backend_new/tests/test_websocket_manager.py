import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.websocket_manager import WebSocketManager
from app.schemas import WebSocketEvent


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


@pytest.mark.asyncio
async def test_disconnect():
    """Test disconnecting a WebSocket."""
    manager = WebSocketManager()
    ws = MagicMock()
    ws.send_json = AsyncMock()

    manager.connect("exec_123", ws)
    manager.disconnect("exec_123", ws)

    assert ws not in manager.connections.get("exec_123", [])
