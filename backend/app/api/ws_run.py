import logging
import time
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.agents.agent_executor import AgentExecutorAgent
from app.models.pipeline import PipelineORM
from app.models.run import RunORM
from app.config import settings

logger = logging.getLogger(__name__)


def _topological_order(agents: list[dict]) -> list[dict]:
    """Return agents in dependency order (simple topological sort)."""
    agent_map = {agent["agent_id"]: agent for agent in agents}
    visited: set[str] = set()
    order: list[dict] = []

    def visit(agent_id: str):
        if agent_id in visited:
            return
        visited.add(agent_id)
        for dep in agent_map.get(agent_id, {}).get("depends_on", []):
            if dep in agent_map:
                visit(dep)
        order.append(agent_map[agent_id])

    for agent in agents:
        visit(agent["agent_id"])
    return order


async def ws_run_handler(websocket: WebSocket, run_id: str):
    await websocket.accept()

    db: Session = SessionLocal()
    try:
        run = db.query(RunORM).filter(RunORM.id == run_id).first()
        if not run:
            await websocket.send_json({"type": "ERROR", "message": "Run not found"})
            await websocket.close()
            return

        pipeline = db.query(PipelineORM).filter(PipelineORM.id == run.pipeline_id).first()
        if not pipeline:
            await websocket.send_json({"type": "ERROR", "message": "Pipeline not found"})
            await websocket.close()
            return

        async def send(event_type: str, data: dict):
            await websocket.send_json({"type": event_type, "run_id": run_id, **data})

        if not settings.active_api_key:
            await send("ERROR", {"message": "No API key configured. Add GEMINI_API_KEY to backend/.env"})
            await websocket.close()
            return

        run.status = "running"
        db.commit()

        await send(
            "RUN_STARTED",
            {
                "pipeline_id": run.pipeline_id,
                "objective": pipeline.objective,
                "inputs": run.inputs,
            },
        )

        blueprint = pipeline.blueprint or {}
        agents = blueprint.get("agents", [])
        ordered_agents = _topological_order(agents)

        executor = AgentExecutorAgent()
        results = []
        context: dict = dict(run.inputs or {})
        start_ms = int(time.time() * 1000)

        for agent_spec in ordered_agents:
            await send(
                "AGENT_STARTED",
                {
                    "agent_id": agent_spec["agent_id"],
                    "agent_name": agent_spec["agent_name"],
                },
            )

            async def _on_code_event(agent_id: str, phase: str, code_preview: str | None):
                await send(
                    "CODE_STATUS",
                    {
                        "agent_id": agent_id,
                        "phase": phase,
                        "elapsed_ms": int(time.time() * 1000) - start_ms,
                        "code_preview": code_preview,
                    },
                )

            result = await executor.execute(agent_spec, context, on_code_event=_on_code_event)
            results.append(result)
            context.update(result.output)

            await send(
                "AGENT_RESULT",
                {
                    "agent_id": result.agent_id,
                    "agent_name": result.agent_name,
                    "status": result.status,
                    "output": result.output,
                    "error": result.error,
                    "duration_ms": result.duration_ms,
                },
            )

        failed = [result for result in results if result.status == "failed"]
        final_status = "failed" if failed else "completed"

        run.status = final_status
        run.results = [result.model_dump() for result in results]
        run.completed_at = datetime.now(timezone.utc)
        db.commit()

        await send(
            "RUN_COMPLETE",
            {
                "status": final_status,
                "total_agents": len(ordered_agents),
                "completed": len([result for result in results if result.status == "completed"]),
                "failed": len(failed),
                "results": [result.model_dump() for result in results],
            },
        )

    except WebSocketDisconnect:
        logger.info("Run WS disconnected: %s", run_id)
    except Exception as exc:
        logger.error("Run WS error for run %s: %s", run_id, exc, exc_info=True)
        try:
            await websocket.send_json({"type": "ERROR", "message": str(exc)})
        except Exception:
            pass
    finally:
        db.close()
