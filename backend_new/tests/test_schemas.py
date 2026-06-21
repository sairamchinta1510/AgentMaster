import pytest
from pydantic import ValidationError
from app.schemas import CreateExecutionRequest, ExecutionResponse, WebSocketEvent


def test_create_execution_request_valid():
    """Test valid execution request."""
    req = CreateExecutionRequest(
        objective="Create a presentation",
        domain="Create PPT",
        config={"max_recursion_depth": 5}
    )
    assert req.objective == "Create a presentation"
    assert req.domain == "Create PPT"
    assert req.config["max_recursion_depth"] == 5


def test_create_execution_request_missing_objective():
    """Test that missing objective raises validation error."""
    with pytest.raises(ValidationError):
        CreateExecutionRequest(domain="Test")


def test_websocket_event_creation():
    """Test WebSocket event factory method."""
    event = WebSocketEvent.create(
        event_type="agent_started",
        execution_id="exec_123",
        data={"agent_id": "agent_456", "agent_name": "TestAgent"}
    )
    assert event.event_type == "agent_started"
    assert event.execution_id == "exec_123"
    assert event.data["agent_id"] == "agent_456"
    assert "timestamp" in event.model_dump()
