import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models.session import ExecutionSession, Phase

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

# In-memory session store (shared across routes)
_sessions: dict[str, ExecutionSession] = {}


class CreateSessionRequest(BaseModel):
    objective: str


@router.post("", status_code=201)
def create_session(body: CreateSessionRequest):
    session_id = str(uuid.uuid4())
    session = ExecutionSession(session_id=session_id, objective=body.objective)
    _sessions[session_id] = session
    return {
        "session_id": session_id,
        "phase": session.phase,
        "objective": session.objective,
    }


@router.get("/{session_id}")
def get_session(session_id: str):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session.session_id,
        "objective": session.objective,
        "phase": session.phase,
        "state": session.state.model_dump() if session.state else {},
    }


@router.get("")
def list_sessions():
    return [
        {"session_id": s.session_id, "objective": s.objective, "phase": s.phase}
        for s in _sessions.values()
    ]
