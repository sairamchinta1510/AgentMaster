from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel


class WebSocketEvent(BaseModel):
    event_type: str
    timestamp: str
    execution_id: str
    data: Dict[str, Any]

    @classmethod
    def create(cls, event_type: str, execution_id: str, data: Dict[str, Any]) -> "WebSocketEvent":
        return cls(
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            execution_id=execution_id,
            data=data
        )


class AgentCreatedEvent(WebSocketEvent):
    event_type: str = "agent_created"


class AgentStartedEvent(WebSocketEvent):
    event_type: str = "agent_started"


class AgentCompletedEvent(WebSocketEvent):
    event_type: str = "agent_completed"


class AgentFailedEvent(WebSocketEvent):
    event_type: str = "agent_failed"


class CritiqueRoundStartedEvent(WebSocketEvent):
    event_type: str = "critique_round_started"


class CritiqueRoundCompletedEvent(WebSocketEvent):
    event_type: str = "critique_round_completed"


class ExecutionStartedEvent(WebSocketEvent):
    event_type: str = "execution_started"


class ExecutionCompletedEvent(WebSocketEvent):
    event_type: str = "execution_completed"


class ExecutionStoppedEvent(WebSocketEvent):
    event_type: str = "execution_stopped"
