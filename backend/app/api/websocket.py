import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.config import settings
from app.agents.agent_master import AgentMasterAgent
from app.agents.agent_producer import AgentProducerAgent
from app.agents.agent_critique import AgentCritiqueAgent, run_critique_loop
from app.library.agent_library import AgentLibrary
from app.models.agent import AgentState
from app.api.routes.sessions import _sessions

router = APIRouter()
logger = logging.getLogger(__name__)
_library = AgentLibrary()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    session = _sessions.get(session_id)
    if not session:
        await websocket.send_json({"type": "ERROR", "message": "Session not found"})
        await websocket.close()
        return

    async def send(event_type: str, data: dict):
        payload = {"type": event_type, "session_id": session_id, **data}
        await websocket.send_json(payload)

    try:
        await send("SESSION_STARTED", {"phase": "DESIGN", "objective": session.objective})

        # Search Agent Library for reusable patterns
        await send("LIBRARY_SEARCH", {"query": session.objective})
        library_results = _library.search(session.objective)
        await send("LIBRARY_RESULTS", {"results": library_results})
        library_context = "\n".join(
            [f"- {r['name']}: {r['objective']}" for r in library_results]
        )

        if not settings.active_api_key:
            await send(
                "ERROR",
                {"message": "No API key configured. Add GEMINI_API_KEY (or OPENAI_API_KEY) to backend/.env"},
            )
            await websocket.close()
            return

        # Design blueprint via AgentMaster
        master = AgentMasterAgent()
        await send("PHASE_UPDATE", {"phase": "DESIGN", "message": "AgentMaster is designing the agent blueprint..."})
        blueprint = await master.design_blueprint(session, library_context)
        await send("BLUEPRINT_READY", {"blueprint": blueprint})

        # Build and emit DAG
        graph = master.build_dag_from_blueprint(blueprint, session_id)
        dag_data = {
            "nodes": [n.model_dump() for n in graph.nodes.values()],
            "edges": [e.model_dump() for e in graph.edges],
        }
        await send("DAG_BUILT", {"dag": dag_data})

        # Process each agent: Producer → Critique loop
        producer = AgentProducerAgent()
        critique = AgentCritiqueAgent()

        approved_count = 0
        final_agent_count = 0
        for agent_spec in blueprint.get("agents", []):
            await send(
                "AGENT_STARTED",
                {
                    "agent_id": agent_spec["agent_id"],
                    "agent_name": agent_spec["agent_name"],
                    "state": AgentState.SPECIFYING,
                },
            )
            agent = await producer.produce(
                agent_spec,
                "design_time",
                session_id,
                session.state.collected_inputs if session.state else {},
            )
            await send(
                "AGENT_PRODUCED",
                {"agent_id": agent.agent_id, "spec": agent.model_dump(exclude={"critique_history"})},
            )

            final_critique, result_agents, iterations = await run_critique_loop(
                agent, critique, producer, "design_time"
            )
            await send(
                "CRITIQUE_COMPLETE",
                {
                    "agent_id": agent.agent_id,
                    "iterations": iterations,
                    "verdict": final_critique.verdict,
                    "quality_score": final_critique.quality_score,
                    "critique": final_critique.model_dump(),
                },
            )
            for final_agent in result_agents:
                final_agent_count += 1
                agent_critique = (
                    final_agent.critique_history[-1]
                    if len(result_agents) > 1 and final_agent.critique_history
                    else final_critique
                )
                state = (
                    AgentState.APPROVED
                    if agent_critique.errors_remaining == 0
                    else AgentState.USER_ESCALATED
                )
                if state == AgentState.APPROVED:
                    approved_count += 1
                await send("AGENT_STATE_CHANGE", {"agent_id": final_agent.agent_id, "state": state})

        # Save approved flow to Agent Library
        lib_id = _library.save_flow(
            session_id=session_id,
            name=f"Flow: {session.objective[:50]}",
            objective=session.objective,
            domain="general",
            graph=graph,
            quality_score=8.0,
        )

        await send(
            "SESSION_COMPLETED",
            {
                "phase": "DESIGN",
                "message": f"Blueprint complete. {approved_count}/{final_agent_count} agents approved. Ready for Dry Run.",
                "agent_count": final_agent_count,
                "library_id": lib_id,
            },
        )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", session_id)
    except Exception as e:
        logger.error("WebSocket error for session %s: %s", session_id, e, exc_info=True)
        try:
            await websocket.send_json({"type": "ERROR", "message": str(e)})
        except Exception:
            pass
