import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.pipeline import PipelineORM
from app.models.run import AgentResult, Run, RunORM

router = APIRouter(prefix="/api/runs", tags=["runs"])
logger = logging.getLogger(__name__)


class CreateRunRequest(BaseModel):
    pipeline_id: str
    inputs: dict = Field(default_factory=dict)


@router.post("", status_code=201, response_model=Run)
def create_run(req: CreateRunRequest, db: Session = Depends(get_db)):
    pipeline = db.query(PipelineORM).filter(PipelineORM.id == req.pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    run_id = str(uuid.uuid4())
    row = RunORM(
        id=run_id,
        pipeline_id=req.pipeline_id,
        inputs=req.inputs,
        status="pending",
        results=[],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _orm_to_run(row)


@router.get("/by-pipeline/{pipeline_id}", response_model=list[Run])
def list_runs_for_pipeline(pipeline_id: str, db: Session = Depends(get_db)):
    rows = (
        db.query(RunORM)
        .filter(RunORM.pipeline_id == pipeline_id)
        .order_by(RunORM.created_at.desc())
        .all()
    )
    return [_orm_to_run(row) for row in rows]


@router.get("/{run_id}", response_model=Run)
def get_run(run_id: str, db: Session = Depends(get_db)):
    row = db.query(RunORM).filter(RunORM.id == run_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    return _orm_to_run(row)


def _orm_to_run(row: RunORM) -> Run:
    results_raw = row.results or []
    results = [AgentResult(**result) if isinstance(result, dict) else result for result in results_raw]
    return Run(
        id=row.id,
        pipeline_id=row.pipeline_id,
        inputs=row.inputs or {},
        status=row.status or "pending",
        results=results,
        created_at=str(row.created_at) if row.created_at else None,
        completed_at=str(row.completed_at) if row.completed_at else None,
    )
