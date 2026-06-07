# backend/app/api/webhooks.py
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.pipeline import PipelineORM
from app.models.run import RunORM

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


@router.post("/{pipeline_id}")
async def trigger_webhook(
    pipeline_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Trigger a pipeline run via webhook.
    Webhook body is merged with pipeline default_inputs as runtime inputs.
    Returns run_id immediately; execution runs in background.
    """
    pipeline = db.query(PipelineORM).filter(PipelineORM.id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    # Parse body (any JSON) — merged over default inputs
    try:
        body = await request.json()
        if not isinstance(body, dict):
            body = {"payload": body}
    except Exception:
        body = {}

    # Merge: default_inputs as base, webhook body overrides
    inputs = {**(pipeline.default_inputs or {}), **{k: str(v) for k, v in body.items()}}

    run_id = str(uuid.uuid4())
    run = RunORM(
        id=run_id,
        pipeline_id=pipeline_id,
        status="pending",
        inputs=inputs,
        triggered_by="webhook",
    )
    db.add(run)
    db.commit()
    logger.info("Webhook triggered run %s for pipeline %s", run_id, pipeline_id)

    from app.agents.headless_run import execute_run_headless
    background_tasks.add_task(execute_run_headless, run_id)

    return {"run_id": run_id, "status": "started"}
