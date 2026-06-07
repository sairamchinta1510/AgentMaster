import logging
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.agents.agent_master import AgentMasterAgent
from app.agents.agent_producer import AgentProducerAgent
from app.agents.agent_critique import AgentCritiqueAgent, run_critique_loop
from app.models.pipeline import PipelineORM
from app.models.agent import AgentState
from app.models.dag import DAGNode, DAGEdge
from app.config import settings
from app.gcs_backup import backup_to_gcs

logger = logging.getLogger(__name__)


async def ws_design_handler(websocket: WebSocket, pipeline_id: str):
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

        await send("DESIGN_STARTED", {"objective": pipeline.objective})

        if not settings.active_api_key:
            await send("ERROR", {"message": "No API key configured. Add GEMINI_API_KEY to backend/.env"})
            await websocket.close()
            return

        master = AgentMasterAgent()
        await send("PHASE_UPDATE", {"phase": "ANALYZING_OBJECTIVE", "message": "Calling LLM to analyze objective and design agent pipeline…"})
        blueprint = await master.design_blueprint_raw(pipeline.objective, on_event=send)
        n_agents = len(blueprint.get("agents", []))
        await send("BLUEPRINT_READY", {"blueprint": blueprint})
        await send("PHASE_UPDATE", {"phase": "BLUEPRINT_READY", "message": f"Blueprint ready — {n_agents} atomic agent(s) identified"})

        dag = master.build_dag_from_blueprint(blueprint, pipeline_id)
        await send(
            "DAG_BUILT",
            {
                "dag": {
                    "nodes": [node.model_dump() for node in dag.nodes.values()],
                    "edges": [edge.model_dump() for edge in dag.edges],
                }
            },
        )
        await send("PHASE_UPDATE", {"phase": "DAG_BUILT", "message": f"Execution graph built — {n_agents} node(s) in pipeline"})

        producer = AgentProducerAgent()
        critique_agent = AgentCritiqueAgent()
        approved_count = 0
        final_agent_count = 0

        for i, agent_spec in enumerate(blueprint.get("agents", []), 1):
            agent_name = agent_spec.get("agent_name", "Agent")
            await send(
                "AGENT_STARTED",
                {
                    "agent_id": agent_spec["agent_id"],
                    "agent_name": agent_name,
                    "state": AgentState.SPECIFYING,
                },
            )
            await send("PHASE_UPDATE", {"phase": "SPECIFYING_AGENT", "message": f"[{i}/{n_agents}] Calling LLM to specify: {agent_name}…"})
            agent = await producer.produce(
                agent_spec,
                "design_time",
                pipeline_id,
                {},
                on_event=send,
            )
            await send(
                "AGENT_PRODUCED",
                {
                    "agent_id": agent.agent_id,
                    "spec": agent.model_dump(exclude={"critique_history"}),
                },
            )
            await send("PHASE_UPDATE", {"phase": "AGENT_SPECIFIED", "message": f"[{i}/{n_agents}] {agent_name} specified — starting critique loop…"})

            final_critique, result_agents, iterations = await run_critique_loop(
                agent, critique_agent, producer, "design_time", on_event=send
            )

            if len(result_agents) > 1:
                orig_node_id = f"node_{agent.agent_id}"
                predecessors = [edge.from_node for edge in dag.edges if edge.to_node == orig_node_id]
                successors = [edge.to_node for edge in dag.edges if edge.from_node == orig_node_id]

                dag.nodes.pop(orig_node_id, None)
                dag.edges = [
                    edge for edge in dag.edges
                    if edge.from_node != orig_node_id and edge.to_node != orig_node_id
                ]
                for node in dag.nodes.values():
                    node.depends_on = [dep for dep in node.depends_on if dep != orig_node_id]

                prev_node_id = None
                for sub_agent in result_agents:
                    new_node_id = f"node_{sub_agent.agent_id}"
                    dag.add_node(DAGNode(
                        node_id=new_node_id,
                        agent_id=sub_agent.agent_id,
                        agent_name=sub_agent.agent_name,
                    ))
                    if prev_node_id:
                        dag.add_edge(DAGEdge(
                            edge_id=f"e_{prev_node_id}_{new_node_id}",
                            from_node=prev_node_id,
                            to_node=new_node_id,
                        ))
                    prev_node_id = new_node_id

                first_node_id = f"node_{result_agents[0].agent_id}"
                for pred in predecessors:
                    dag.add_edge(DAGEdge(
                        edge_id=f"e_{pred}_{first_node_id}",
                        from_node=pred,
                        to_node=first_node_id,
                    ))

                last_node_id = f"node_{result_agents[-1].agent_id}"
                for succ in successors:
                    dag.add_edge(DAGEdge(
                        edge_id=f"e_{last_node_id}_{succ}",
                        from_node=last_node_id,
                        to_node=succ,
                    ))

                await send(
                    "DAG_UPDATED",
                    {
                        "dag": {
                            "nodes": [node.model_dump() for node in dag.nodes.values()],
                            "edges": [edge.model_dump() for edge in dag.edges],
                        },
                        "message": (
                            f"Agent '{agent.agent_name}' decomposed into "
                            f"{len(result_agents)} atomic sub-agents"
                        ),
                    },
                )

            for final_agent in result_agents:
                final_agent_count += 1
                agent_critique = (
                    final_agent.critique_history[-1]
                    if len(result_agents) > 1 and final_agent.critique_history
                    else final_critique
                )
                await send(
                    "CRITIQUE_COMPLETE",
                    {
                        "agent_id": final_agent.agent_id,
                        "iterations": iterations,
                        "verdict": agent_critique.verdict,
                        "quality_score": agent_critique.quality_score,
                        "critique": agent_critique.model_dump(),
                    },
                )

                state = (
                    AgentState.APPROVED
                    if agent_critique.errors_remaining == 0
                    else AgentState.USER_ESCALATED
                )
                if state == AgentState.APPROVED:
                    approved_count += 1
                await send("AGENT_STATE_CHANGE", {"agent_id": final_agent.agent_id, "state": state})

        input_fields = [
            {
                "name": input_field["name"],
                "type": input_field.get("type", "string"),
                "description": input_field.get("description", ""),
                "required": input_field.get("required", True),
            }
            for input_field in blueprint.get("required_inputs", [])
        ]
        pipeline.blueprint = blueprint
        pipeline.input_schema = input_fields
        pipeline.updated_at = datetime.now(timezone.utc)
        db.commit()
        backup_to_gcs()

        # Register or unregister schedule based on trigger_config
        trigger = blueprint.get("trigger_config", {})
        if trigger.get("mode") == "scheduled":
            from app.scheduler import register_pipeline_schedule
            interval = int(trigger.get("interval_minutes") or 5)
            register_pipeline_schedule(pipeline_id, interval)
        else:
            from app.scheduler import unregister_pipeline_schedule
            unregister_pipeline_schedule(pipeline_id)

        await send(
            "DESIGN_COMPLETE",
            {
                "message": f"Design complete. {approved_count}/{final_agent_count} agents approved.",
                "agent_count": final_agent_count,
                "approved_count": approved_count,
                "input_schema": input_fields,
            },
        )

    except WebSocketDisconnect:
        logger.info("Design WS disconnected: %s", pipeline_id)
    except Exception as exc:
        logger.error("Design WS error for pipeline %s: %s", pipeline_id, exc, exc_info=True)
        try:
            await websocket.send_json({"type": "ERROR", "message": str(exc)})
        except Exception:
            pass
    finally:
        db.close()
