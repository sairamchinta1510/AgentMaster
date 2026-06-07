import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.pipeline import PipelineORM, Pipeline, PipelineSummary
from app.gcs_backup import backup_to_gcs

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])
logger = logging.getLogger(__name__)


class CreatePipelineRequest(BaseModel):
    objective: str
    name: str = ""


@router.post("", status_code=201, response_model=Pipeline)
def create_pipeline(req: CreatePipelineRequest, db: Session = Depends(get_db)):
    pipeline_id = str(uuid.uuid4())
    name = req.name or req.objective[:60]
    row = PipelineORM(
        id=pipeline_id,
        objective=req.objective,
        name=name,
        input_schema=[],
        blueprint={},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    backup_to_gcs()
    return _orm_to_pipeline(row)


@router.get("", response_model=list[PipelineSummary])
def list_pipelines(db: Session = Depends(get_db)):
    rows = db.query(PipelineORM).order_by(PipelineORM.created_at.desc()).all()
    return [_orm_to_summary(row) for row in rows]


@router.get("/{pipeline_id}", response_model=Pipeline)
def get_pipeline(pipeline_id: str, db: Session = Depends(get_db)):
    row = db.query(PipelineORM).filter(PipelineORM.id == pipeline_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return _orm_to_pipeline(row)


@router.delete("/{pipeline_id}", status_code=204)
def delete_pipeline(pipeline_id: str, db: Session = Depends(get_db)):
    row = db.query(PipelineORM).filter(PipelineORM.id == pipeline_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    db.delete(row)
    db.commit()
    backup_to_gcs()


def _orm_to_pipeline(row: PipelineORM) -> Pipeline:
    return Pipeline(
        id=row.id,
        objective=row.objective,
        name=row.name,
        input_schema=row.input_schema or [],
        blueprint=row.blueprint or {},
        created_at=str(row.created_at) if row.created_at else None,
        updated_at=str(row.updated_at) if row.updated_at else None,
    )


def _orm_to_summary(row: PipelineORM) -> PipelineSummary:
    blueprint = row.blueprint or {}
    agent_count = len(blueprint.get("agents", []))
    return PipelineSummary(
        id=row.id,
        objective=row.objective,
        name=row.name,
        agent_count=agent_count,
        created_at=str(row.created_at) if row.created_at else None,
    )
