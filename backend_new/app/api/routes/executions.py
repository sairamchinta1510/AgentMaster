import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Execution, Agent
from app.schemas import CreateExecutionRequest, ExecutionResponse
from app.agents import AgentMaster

router = APIRouter()


@router.post("/api/executions", response_model=ExecutionResponse)
def create_execution(request: CreateExecutionRequest, db: Session = Depends(get_db)):
    """Create a new execution."""
    exec_id = str(uuid.uuid4())

    execution = Execution(
        id=exec_id,
        objective=request.objective,
        domain=request.domain,
        status="planning",
        config=request.config
    )
    db.add(execution)
    db.commit()

    # Create root agent via AgentMaster
    orchestrator = AgentMaster(
        execution_id=exec_id,
        objective=request.objective,
        domain=request.domain,
        db_session=db
    )
    plan = orchestrator.plan()

    # Update execution with root agent
    execution.root_agent_id = plan["root_agent_id"]
    db.commit()

    db.refresh(execution)
    return ExecutionResponse(**execution.to_dict())


@router.get("/api/executions/{execution_id}", response_model=ExecutionResponse)
def get_execution(execution_id: str, db: Session = Depends(get_db)):
    """Get execution by ID."""
    execution = db.query(Execution).filter_by(id=execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return ExecutionResponse(**execution.to_dict())
