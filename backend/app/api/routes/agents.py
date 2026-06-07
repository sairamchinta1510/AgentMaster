from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.api.routes.sessions import _sessions

router = APIRouter(prefix="/api/sessions", tags=["agents"])


class UserInputRequest(BaseModel):
    input_name: str
    value: str


@router.post("/{session_id}/input")
def provide_input(session_id: str, body: UserInputRequest):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.state:
        session.state.collected_inputs[body.input_name] = body.value
    return {"status": "input_received", "input_name": body.input_name}
