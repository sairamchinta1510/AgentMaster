# backend/app/scheduler.py
import logging
import uuid

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler()


def get_scheduler() -> AsyncIOScheduler:
    return _scheduler


async def _run_pipeline_scheduled(pipeline_id: str) -> None:
    """Create a run record and execute headlessly for a scheduled pipeline."""
    from app.db import SessionLocal
    from app.models.pipeline import PipelineORM
    from app.models.run import RunORM
    from app.agents.headless_run import execute_run_headless

    db = SessionLocal()
    try:
        pipeline = db.query(PipelineORM).filter(PipelineORM.id == pipeline_id).first()
        if not pipeline:
            logger.warning("Scheduled pipeline %s not found — removing job", pipeline_id)
            unregister_pipeline_schedule(pipeline_id)
            db.close()
            return

        run_id = str(uuid.uuid4())
        run = RunORM(
            id=run_id,
            pipeline_id=pipeline_id,
            status="pending",
            inputs=pipeline.default_inputs or {},
            triggered_by="schedule",
        )
        db.add(run)
        db.commit()
        logger.info("Scheduler created run %s for pipeline %s", run_id, pipeline_id)
    finally:
        db.close()

    await execute_run_headless(run_id)


def register_pipeline_schedule(pipeline_id: str, interval_minutes: int) -> None:
    job_id = f"pipeline_{pipeline_id}"
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)
    _scheduler.add_job(
        _run_pipeline_scheduled,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id=job_id,
        args=[pipeline_id],
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    logger.info("Registered schedule: pipeline %s every %d min", pipeline_id, interval_minutes)


def unregister_pipeline_schedule(pipeline_id: str) -> None:
    job_id = f"pipeline_{pipeline_id}"
    job = _scheduler.get_job(job_id)
    if job:
        _scheduler.remove_job(job_id)
        logger.info("Unregistered schedule for pipeline %s", pipeline_id)


def load_all_schedules() -> None:
    """Called on startup — register all pipelines with mode=scheduled."""
    from app.db import SessionLocal
    from app.models.pipeline import PipelineORM

    db = SessionLocal()
    try:
        pipelines = db.query(PipelineORM).all()
        count = 0
        for pipeline in pipelines:
            blueprint = pipeline.blueprint or {}
            trigger = blueprint.get("trigger_config", {})
            if trigger.get("mode") == "scheduled":
                interval = int(trigger.get("interval_minutes") or 5)
                register_pipeline_schedule(pipeline.id, interval)
                count += 1
        logger.info("Loaded %d scheduled pipelines on startup", count)
    finally:
        db.close()
