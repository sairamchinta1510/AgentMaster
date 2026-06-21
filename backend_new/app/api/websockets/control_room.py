from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Execution
from app.services import websocket_manager, ExecutionManager
from datetime import datetime

router = APIRouter()


@router.websocket("/ws/control-room/{execution_id}")
async def control_room_websocket(websocket: WebSocket, execution_id: str, db: Session = Depends(get_db)):
    """
    Control Room WebSocket - for execution phase.
    Broadcasts real-time agent execution events.
    """
    await websocket.accept()
    websocket_manager.connect(execution_id, websocket)

    # Check if execution exists
    execution = db.query(Execution).filter_by(id=execution_id).first()
    if not execution:
        await websocket.close(code=1008, reason="Execution not found")
        return

    # Start execution if not already running
    if execution.status == "planning":
        execution.status = "running"
        execution.started_at = datetime.utcnow()
        db.commit()

        # Run execution manager
        manager = ExecutionManager(execution_id=execution_id, db_session=db)
        await manager.execute()

    try:
        while True:
            # Wait for client messages (e.g., stop, pause)
            data = await websocket.receive_json()

            if data.get("action") == "stop":
                # Handle stop execution
                execution.status = "stopped_by_user"
                execution.stopped_at = datetime.utcnow()
                execution.stopped_by = "user"
                db.commit()
                break

    except WebSocketDisconnect:
        websocket_manager.disconnect(execution_id, websocket)
