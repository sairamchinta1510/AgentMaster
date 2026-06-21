from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Agent
from app.schemas import AgentResponse

router = APIRouter()


@router.get("/api/agents/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """Get agent by ID."""
    agent = db.query(Agent).filter_by(id=agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse(**agent.to_dict())
