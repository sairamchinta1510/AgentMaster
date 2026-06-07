# backend/app/agents/headless_run.py
"""Non-WebSocket pipeline execution for scheduled and webhook-triggered runs."""
import logging
from datetime import datetime, timezone

from app.db import SessionLocal
from app.agents.agent_executor import AgentExecutorAgent
from app.api.ws_run import _topological_order
from app.models.pipeline import PipelineORM
from app.models.run import RunORM
from app.gcs_backup import backup_to_gcs

logger = logging.getLogger(__name__)


async def execute_run_headless(run_id: str) -> None:
    """Execute a pipeline run without WebSocket — updates DB only."""
    db = SessionLocal()
    try:
        run = db.query(RunORM).filter(RunORM.id == run_id).first()
        if not run:
            logger.error("Headless run: run %s not found", run_id)
            return

        pipeline = db.query(PipelineORM).filter(PipelineORM.id == run.pipeline_id).first()
        if not pipeline:
            logger.error("Headless run: pipeline %s not found", run.pipeline_id)
            run.status = "failed"
            db.commit()
            return

        run.status = "running"
        db.commit()

        blueprint = pipeline.blueprint or {}
        agents = blueprint.get("agents", [])
        ordered_agents = _topological_order(agents)

        executor = AgentExecutorAgent()
        results = []
        context: dict = dict(run.inputs or {})

        for agent_spec in ordered_agents:
            result = await executor.execute(agent_spec, context)
            results.append(result)
            context.update(result.output)
            logger.info("Headless run %s: agent %s → %s", run_id, agent_spec["agent_id"], result.status)

        failed = [r for r in results if r.status == "failed"]
        final_status = "failed" if failed else "completed"

        run.status = final_status
        run.results = [r.model_dump() for r in results]
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        backup_to_gcs()

        logger.info("Headless run %s complete: %s (%d agents)", run_id, final_status, len(results))

    except Exception as exc:
        logger.error("Headless run %s failed: %s", run_id, exc, exc_info=True)
        try:
            run.status = "failed"
            db.commit()
        except Exception:
            pass
    finally:
        db.close()
