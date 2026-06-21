from typing import Dict, List
from fastapi import WebSocket
from app.schemas.websocket import WebSocketEvent
import logging

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and broadcasts events."""

    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}

    def connect(self, execution_id: str, websocket: WebSocket) -> None:
        """Register a new WebSocket connection for an execution."""
        if execution_id not in self.connections:
            self.connections[execution_id] = []
        self.connections[execution_id].append(websocket)
        logger.info(f"WebSocket connected for execution {execution_id}")

    def disconnect(self, execution_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if execution_id in self.connections:
            if websocket in self.connections[execution_id]:
                self.connections[execution_id].remove(websocket)
            if not self.connections[execution_id]:
                del self.connections[execution_id]
        logger.info(f"WebSocket disconnected for execution {execution_id}")

    async def broadcast(self, execution_id: str, event: WebSocketEvent) -> None:
        """Broadcast an event to all connected clients for an execution."""
        if execution_id not in self.connections:
            return

        event_dict = event.model_dump()
        disconnected = []

        for websocket in self.connections[execution_id]:
            try:
                await websocket.send_json(event_dict)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(websocket)

        # Clean up disconnected websockets
        for ws in disconnected:
            self.disconnect(execution_id, ws)


# Global singleton
websocket_manager = WebSocketManager()
