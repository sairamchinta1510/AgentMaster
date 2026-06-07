import json
import logging
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.agents.agent_producer import AgentProducerAgent
from app.agents.agent_critique import AgentCritiqueAgent, run_critique_loop
from app.models.pipeline import PipelineORM
from app.models.agent import AgentState
from app.config import settings
from app.gcs_backup import backup_to_gcs

logger = logging.getLogger(__name__)


async def ws_extend_handler(websocket: WebSocket, pipeline_id: str):
    """
    Extend an existing pipeline with new agents only.
    
    Protocol:
    1. Client connects
    2. Server sends EXTEND_READY
    3. Client sends JSON: {"new_agents": [...], "new_edges": [...]}
    4. Server produces + critiques each new agent (emits same events as ws_design)
    5. Server merges new agents into existing blueprint, saves to DB
    6. Server sends EXTEND_COMPLETE
    """
    await websocket.accept()

    db: Session = SessionLocal()
    try:
        pipeline = db.query(PipelineORM).filter(PipelineORM.id == pipeline_id).first()
        if not pipeline:
            await websocket.send_json({"type": "ERROR", "message": "Pipeline not found"})
            await websocket.close()
            return

        async def send(event_type: str, data: dict):
            await websocket.send_json({"type": event_type, "pipeline_id": pipeline_id, **data})

        if not settings.active_api_key:
            await send("ERROR", {"message": "No API key configured"})
            await websocket.close()
            return

        await send("EXTEND_READY", {"message": "Ready to receive extension agents"})

        # Wait for client to send the selected new agents
        raw = await websocket.receive_text()
        payload = json.loads(raw)
        new_agent_specs = payload.get("new_agents", [])
        new_edges = payload.get("new_edges", [])

        if not new_agent_specs:
            await send("ERROR", {"message": "No agents provided for extension"})
            await websocket.close()
            return

        n_new = len(new_agent_specs)
        await send("PHASE_UPDATE", {
            "phase": "EXTENDING",
            "message": f"Extending pipeline with {n_new} new agent(s)…",
        })

        producer = AgentProducerAgent()
        critique_agent = AgentCritiqueAgent()
        approved_new = []

        for i, agent_spec in enumerate(new_agent_specs, 1):
            agent_name = agent_spec.get("agent_name", "Agent")
            await send("AGENT_STARTED", {
                "agent_id": agent_spec["agent_id"],
                "agent_name": agent_name,
                "state": AgentState.SPECIFYING,
            })
            await send("PHASE_UPDATE", {
                "phase": "SPECIFYING_AGENT",
                "message": f"[{i}/{n_new}] Calling LLM to specify: {agent_name}…",
            })

            agent = await producer.produce(agent_spec, "design_time", pipeline_id, {}, on_event=send)

            await send("AGENT_PRODUCED", {
                "agent_id": agent.agent_id,
                "spec": agent.model_dump(exclude={"critique_history"}),
            })
            await send("PHASE_UPDATE", {
                "phase": "AGENT_SPECIFIED",
                "message": f"[{i}/{n_new}] {agent_name} specified — starting critique…",
            })

            final_critique, result_agents, iterations = await run_critique_loop(
                agent, critique_agent, producer, "design_time", on_event=send
            )

            await send("CRITIQUE_COMPLETE", {
                "agent_id": agent.agent_id,
                "iterations": iterations,
                "verdict": final_critique.verdict,
                "quality_score": final_critique.quality_score,
                "critique": final_critique.model_dump(),
            })

            for final_agent in result_agents:
                state = AgentState.APPROVED if final_critique.errors_remaining == 0 else AgentState.USER_ESCALATED
                await send("AGENT_STATE_CHANGE", {"agent_id": final_agent.agent_id, "state": state})
                approved_new.append(final_agent.model_dump(exclude={"critique_history"}))

        # Merge into existing blueprint
        existing_blueprint = pipeline.blueprint or {}
        existing_agents = existing_blueprint.get("agents", [])
        existing_edges = existing_blueprint.get("edges", [])

        merged_blueprint = {
            **existing_blueprint,
            "agents": existing_agents + new_agent_specs,
            "edges": existing_edges + new_edges,
        }

        pipeline.blueprint = merged_blueprint
        pipeline.updated_at = datetime.now(timezone.utc)
        db.commit()
        backup_to_gcs()

        total_agents = len(merged_blueprint["agents"])
        await send("EXTEND_COMPLETE", {
            "message": f"Extension complete. Pipeline now has {total_agents} agents.",
            "new_agent_count": n_new,
            "total_agent_count": total_agents,
            "blueprint": merged_blueprint,
        })

    except WebSocketDisconnect:
        logger.info("Extend WS disconnected: %s", pipeline_id)
    except Exception as exc:
        logger.error("Extend WS error for pipeline %s: %s", pipeline_id, exc, exc_info=True)
        try:
            await websocket.send_json({"type": "ERROR", "message": str(exc)})
        except Exception:
            pass
    finally:
        db.close()
