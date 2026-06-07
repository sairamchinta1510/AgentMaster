from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agents.agent_master import AgentMasterAgent
from app.agents.agent_producer import AgentProducerAgent
from app.api.routes.sessions import _sessions
from app.api.websocket import router as legacy_websocket_router
from app.config import settings
from app.main import app
from app.models.agent import AtomicAgent, CritiqueResult, CritiqueVerdict
from app.models.session import ExecutionSession


def _approved_critique(agent_id: str, agent_name: str, iteration: int = 1) -> CritiqueResult:
    return CritiqueResult(
        critique_id=f"{agent_id}_critique_iter_{iteration}",
        target_agent=agent_id,
        target_agent_name=agent_name,
        phase="design_time",
        iteration=iteration,
        verdict=CritiqueVerdict.APPROVED,
        quality_score=9.0,
        errors_remaining=0,
    )


def _needs_revision_critique(agent_id: str, agent_name: str, iteration: int = 1) -> CritiqueResult:
    return CritiqueResult(
        critique_id=f"{agent_id}_critique_iter_{iteration}",
        target_agent=agent_id,
        target_agent_name=agent_name,
        phase="design_time",
        iteration=iteration,
        verdict=CritiqueVerdict.NEEDS_REVISION,
        quality_score=3.0,
        errors_remaining=1,
    )


def test_ws_extend_emits_state_changes_for_each_decomposed_agent():
    initial_agent = AtomicAgent(agent_id="writer", agent_name="WriterAgent", session_id="p1")
    part_1 = AtomicAgent(agent_id="writer_part_1", agent_name="DraftAgent", session_id="p1")
    part_2 = AtomicAgent(agent_id="writer_part_2", agent_name="EditAgent", session_id="p1")
    part_1.critique_history = [_approved_critique("writer_part_1", "DraftAgent")]
    part_2.critique_history = [_approved_critique("writer_part_2", "EditAgent")]

    with TestClient(app) as client:
        pipeline_id = client.post("/api/pipelines", json={"objective": "Extend pipeline"}).json()["id"]

        with (
            patch.object(settings, "gemini_api_key", "test-key"),
            patch.object(settings, "openai_api_key", ""),
            patch.object(AgentProducerAgent, "produce", new=AsyncMock(return_value=initial_agent)),
            patch(
                "app.api.ws_extend.run_critique_loop",
                new=AsyncMock(
                    return_value=(_needs_revision_critique("writer", "WriterAgent"), [part_1, part_2], 1)
                ),
            ),
            patch("app.api.ws_extend.backup_to_gcs"),
        ):
            with client.websocket_connect(f"/ws/extend/{pipeline_id}") as websocket:
                ready = websocket.receive_json()
                assert ready["type"] == "EXTEND_READY"

                websocket.send_json(
                    {
                        "new_agents": [{"agent_id": "writer", "agent_name": "WriterAgent"}],
                        "new_edges": [],
                    }
                )

                events = [ready]
                for _ in range(20):
                    event = websocket.receive_json()
                    events.append(event)
                    if event["type"] in {"EXTEND_COMPLETE", "ERROR"}:
                        break
                else:
                    raise AssertionError("ws_extend flow did not finish within 20 events")

    assert events[-1]["type"] == "EXTEND_COMPLETE"
    state_changes = {
        event["agent_id"]: event["state"] for event in events if event["type"] == "AGENT_STATE_CHANGE"
    }
    assert state_changes == {
        "writer_part_1": "APPROVED",
        "writer_part_2": "APPROVED",
    }


def test_legacy_websocket_counts_and_emits_each_decomposed_agent():
    legacy_app = FastAPI()
    legacy_app.include_router(legacy_websocket_router)

    session = ExecutionSession(session_id="session-1", objective="Plan a report")
    _sessions[session.session_id] = session

    blueprint = {"agents": [{"agent_id": "planner", "agent_name": "PlannerAgent"}]}
    initial_agent = AtomicAgent(agent_id="planner", agent_name="PlannerAgent", session_id=session.session_id)
    part_1 = AtomicAgent(agent_id="planner_part_1", agent_name="ResearchAgent", session_id=session.session_id)
    part_2 = AtomicAgent(agent_id="planner_part_2", agent_name="OutlineAgent", session_id=session.session_id)
    part_1.critique_history = [_approved_critique("planner_part_1", "ResearchAgent")]
    part_2.critique_history = [_approved_critique("planner_part_2", "OutlineAgent")]
    empty_graph = MagicMock(nodes={}, edges=[])

    try:
        with TestClient(legacy_app) as client:
            with (
                patch.object(settings, "gemini_api_key", "test-key"),
                patch.object(settings, "openai_api_key", ""),
                patch.object(AgentMasterAgent, "design_blueprint", new=AsyncMock(return_value=blueprint)),
                patch.object(AgentMasterAgent, "build_dag_from_blueprint", return_value=empty_graph),
                patch.object(AgentProducerAgent, "produce", new=AsyncMock(return_value=initial_agent)),
                patch(
                    "app.api.websocket.run_critique_loop",
                    new=AsyncMock(
                        return_value=(_needs_revision_critique("planner", "PlannerAgent"), [part_1, part_2], 1)
                    ),
                ),
                patch("app.api.websocket._library.search", return_value=[]),
                patch("app.api.websocket._library.save_flow", return_value="lib-1"),
            ):
                with client.websocket_connect(f"/ws/{session.session_id}") as websocket:
                    events = []
                    for _ in range(20):
                        event = websocket.receive_json()
                        events.append(event)
                        if event["type"] in {"SESSION_COMPLETED", "ERROR"}:
                            break
                    else:
                        raise AssertionError("legacy websocket flow did not finish within 20 events")
    finally:
        _sessions.pop(session.session_id, None)

    assert events[-1]["type"] == "SESSION_COMPLETED"
    assert events[-1]["message"] == "Blueprint complete. 2/2 agents approved. Ready for Dry Run."
    assert events[-1]["agent_count"] == 2
    state_changes = {
        event["agent_id"]: event["state"] for event in events if event["type"] == "AGENT_STATE_CHANGE"
    }
    assert state_changes == {
        "planner_part_1": "APPROVED",
        "planner_part_2": "APPROVED",
    }
