from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.agents.agent_master import AgentMasterAgent
from app.agents.agent_producer import AgentProducerAgent
from app.config import settings
from app.main import app
from app.models.agent import AtomicAgent, CritiqueResult, CritiqueVerdict


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


def test_ws_design_replaces_decomposed_node_with_series():
    blueprint = {
        "agents": [
            {"agent_id": "fetch", "agent_name": "FetchAgent"},
            {"agent_id": "middle", "agent_name": "MiddleAgent"},
            {"agent_id": "publish", "agent_name": "PublishAgent"},
        ],
        "edges": [
            {"from": "fetch", "to": "middle"},
            {"from": "middle", "to": "publish"},
        ],
        "required_inputs": [],
        "trigger_config": {"mode": "manual"},
    }
    fetch_agent = AtomicAgent(agent_id="fetch", agent_name="FetchAgent", session_id="s1")
    middle_agent = AtomicAgent(agent_id="middle", agent_name="MiddleAgent", session_id="s1")
    publish_agent = AtomicAgent(agent_id="publish", agent_name="PublishAgent", session_id="s1")
    middle_part_1 = AtomicAgent(agent_id="middle_part_1", agent_name="ParseAgent", session_id="s1")
    middle_part_2 = AtomicAgent(agent_id="middle_part_2", agent_name="AnalyzeAgent", session_id="s1")

    critique_results = [
        (_approved_critique("fetch", "FetchAgent"), [fetch_agent], 1),
        (_approved_critique("middle", "MiddleAgent", iteration=2), [middle_part_1, middle_part_2], 2),
        (_approved_critique("publish", "PublishAgent"), [publish_agent], 1),
    ]

    with TestClient(app) as client:
        pipeline_id = client.post("/api/pipelines", json={"objective": "Test websocket DAG surgery"}).json()["id"]

        with (
            patch.object(settings, "gemini_api_key", "test-key"),
            patch.object(settings, "openai_api_key", ""),
            patch.object(AgentMasterAgent, "design_blueprint_raw", new=AsyncMock(return_value=blueprint)),
            patch.object(
                AgentProducerAgent,
                "produce",
                new=AsyncMock(side_effect=[fetch_agent, middle_agent, publish_agent]),
            ),
            patch("app.api.ws_design.run_critique_loop", new=AsyncMock(side_effect=critique_results)),
            patch("app.api.ws_design.backup_to_gcs"),
            patch("app.scheduler.unregister_pipeline_schedule"),
        ):
            with client.websocket_connect(f"/ws/design/{pipeline_id}") as websocket:
                events = []
                for _ in range(50):
                    event = websocket.receive_json()
                    events.append(event)
                    if event["type"] in {"DESIGN_COMPLETE", "ERROR"}:
                        break
                else:
                    raise AssertionError("WebSocket design flow did not finish within 50 events")

    dag_updated = next(event for event in events if event["type"] == "DAG_UPDATED")
    node_ids = {node["node_id"] for node in dag_updated["dag"]["nodes"]}
    edge_pairs = {(edge["from_node"], edge["to_node"]) for edge in dag_updated["dag"]["edges"]}
    nodes_by_id = {node["node_id"]: node for node in dag_updated["dag"]["nodes"]}

    assert "node_middle" not in node_ids
    assert {"node_fetch", "node_middle_part_1", "node_middle_part_2", "node_publish"} <= node_ids
    assert ("node_fetch", "node_middle_part_1") in edge_pairs
    assert ("node_middle_part_1", "node_middle_part_2") in edge_pairs
    assert ("node_middle_part_2", "node_publish") in edge_pairs
    assert all("node_middle" not in edge for edge in edge_pairs)
    assert nodes_by_id["node_middle_part_1"]["depends_on"] == ["node_fetch"]
    assert nodes_by_id["node_middle_part_2"]["depends_on"] == ["node_middle_part_1"]
    assert nodes_by_id["node_publish"]["depends_on"] == ["node_middle_part_2"]

    critique_complete_ids = [
        event["agent_id"] for event in events if event["type"] == "CRITIQUE_COMPLETE"
    ]
    state_change_ids = [
        event["agent_id"] for event in events if event["type"] == "AGENT_STATE_CHANGE"
    ]

    assert "middle" not in critique_complete_ids
    assert "middle" not in state_change_ids
    assert "middle_part_1" in critique_complete_ids
    assert "middle_part_2" in critique_complete_ids
    assert "middle_part_1" in state_change_ids
    assert "middle_part_2" in state_change_ids
