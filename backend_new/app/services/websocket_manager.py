from typing import Dict, List, Optional
from fastapi import WebSocket
from app.schemas.websocket import WebSocketEvent
from app.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and broadcasts events."""

    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}
        self.ping_tasks: Dict[str, asyncio.Task] = {}
        self.ping_interval: int = settings.websocket_ping_interval

    def connect(self, execution_id: str, websocket: WebSocket) -> None:
        """Register a new WebSocket connection for an execution."""
        if execution_id not in self.connections:
            self.connections[execution_id] = []
            # Start ping task for this execution when first connection is made
            self.ping_tasks[execution_id] = asyncio.create_task(
                self._ping_keep_alive(execution_id)
            )
        self.connections[execution_id].append(websocket)
        logger.info(f"WebSocket connected for execution {execution_id}")

    def disconnect(self, execution_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if execution_id in self.connections:
            if websocket in self.connections[execution_id]:
                self.connections[execution_id].remove(websocket)
            if not self.connections[execution_id]:
                del self.connections[execution_id]
                # Cancel ping task when last connection is removed
                if execution_id in self.ping_tasks:
                    self.ping_tasks[execution_id].cancel()
                    del self.ping_tasks[execution_id]
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

    async def _ping_keep_alive(self, execution_id: str) -> None:
        """
        Send periodic ping events to keep connections alive and detect stale connections.
        Enforces WebSocket ping interval constraint: 30 seconds.
        """
        try:
            while execution_id in self.connections and self.connections[execution_id]:
                await asyncio.sleep(self.ping_interval)

                if execution_id not in self.connections:
                    break

                ping_event = WebSocketEvent.create(
                    event_type="ping",
                    execution_id=execution_id,
                    data={"timestamp": None}
                )

                # Send ping to all connected clients
                await self.broadcast(execution_id, ping_event)
        except asyncio.CancelledError:
            logger.info(f"Ping keep-alive task cancelled for execution {execution_id}")
        except Exception as e:
            logger.error(f"Error in WebSocket ping keep-alive: {e}")


# Global singleton
websocket_manager = WebSocketManager()
