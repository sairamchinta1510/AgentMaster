from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import websocket_manager

router = APIRouter()


@router.websocket("/ws/studio/{execution_id}")
async def studio_websocket(websocket: WebSocket, execution_id: str, db: Session = Depends(get_db)):
    """
    Studio WebSocket - for planning phase.
    User connects here to see agent plan being built.
    """
    await websocket.accept()
    websocket_manager.connect(execution_id, websocket)

    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_json()

            # Handle client messages (e.g., approve plan)
            if data.get("action") == "approve":
                # Transition to run phase (handled by client navigating to control room)
                pass

    except WebSocketDisconnect:
        websocket_manager.disconnect(execution_id, websocket)
