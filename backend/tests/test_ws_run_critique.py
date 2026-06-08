import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.db import SessionLocal
from app.models.pipeline import PipelineORM
from app.models.run import AgentResult

client = TestClient(app)


@pytest.mark.asyncio
async def test_critique_node_triggers_rerun_on_needs_fix(monkeypatch):
    """When a critique node finds NEEDS_FIX, it calls the target agent again with fix instructions."""
    from app.api.ws_run import _run_critique_node

    target_agent_spec = {
        "agent_id": "identify_001",
        "agent_name": "IdentifyLogStorage",
        "agent_type": "task",
        "description": "Identifies log storage",
        "input_schema": {"repository_path": {"type": "string"}},
        "output_schema": {"log_storage_mechanism": {"type": "string"}},
        "depends_on": [],
    }
    critique_spec = {
        "agent_id": "critique_001",
        "agent_name": "CritiqueLogStorage",
        "agent_type": "critique",
        "description": "Validates log storage identification",
        "depends_on": ["identify_001"],
    }

    results_store = {}
    rerun_calls = []

    async def mock_rerun(agent_spec, context, fix_instructions):
        rerun_calls.append(fix_instructions)
        results_store["identify_001"] = MagicMock(
            status="completed",
            output={"log_storage_mechanism": "cloudwatch"},
            error=None,
        )

    from app.agents.runtime_critique import CritiqueLoopResult

    mock_executor = MagicMock()
    mock_executor.run_exec_critique = AsyncMock(
        return_value=CritiqueLoopResult(
            verdict="APPROVED",
            quality_score=9.0,
            iterations=3,
        )
    )

    with patch("app.api.ws_run.CritiqueNodeExecutor", return_value=mock_executor):
        await _run_critique_node(
            critique_spec=critique_spec,
            ordered_agents=[target_agent_spec],
            results=results_store,
            context={"REPOSITORY_PATH": "/tmp/tmpabc"},
            send=AsyncMock(),
            rerun_agent=mock_rerun,
        )

    mock_executor.run_exec_critique.assert_called_once()


@pytest.mark.asyncio
async def test_critique_node_skipped_if_no_depends_on():
    """Critique node with empty depends_on should complete without calling LLM."""
    from app.api.ws_run import _run_critique_node
    from app.agents.runtime_critique import CritiqueLoopResult

    mock_executor = MagicMock()
    mock_executor.run_exec_critique = AsyncMock(
        return_value=CritiqueLoopResult(
            verdict="APPROVED",
            quality_score=9.0,
            iterations=3,
        )
    )

    with patch("app.api.ws_run.CritiqueNodeExecutor", return_value=mock_executor):
        await _run_critique_node(
            critique_spec={"agent_id": "c1", "agent_name": "C", "agent_type": "critique", "depends_on": []},
            ordered_agents=[],
            results={},
            context={},
            send=AsyncMock(),
            rerun_agent=AsyncMock(),
        )

    mock_executor.run_exec_critique.assert_not_called()


@pytest.mark.asyncio
async def test_critique_node_fails_if_any_dependency_needs_fix():
    """A critique node with multiple dependencies should stay failed if any target needs fixes."""
    from app.api.ws_run import _run_critique_node
    from app.agents.runtime_critique import CritiqueLoopResult

    ordered_agents = [
        {
            "agent_id": "a1",
            "agent_name": "A1",
            "agent_type": "task",
            "description": "First",
            "input_schema": {},
            "output_schema": {},
            "depends_on": [],
        },
        {
            "agent_id": "a2",
            "agent_name": "A2",
            "agent_type": "task",
            "description": "Second",
            "input_schema": {},
            "output_schema": {},
            "depends_on": [],
        },
    ]
    results = {
        "a1": MagicMock(status="completed", output={}, error=None),
        "a2": MagicMock(status="completed", output={}, error=None),
    }

    mock_executor = MagicMock()
    mock_executor.run_exec_critique = AsyncMock(
        side_effect=[
            CritiqueLoopResult(
                verdict="NEEDS_FIX",
                quality_score=2.0,
                iterations=3,
                issues=["broken"],
                fix_instructions="Fix first agent",
            ),
            CritiqueLoopResult(
                verdict="APPROVED",
                quality_score=9.0,
                iterations=3,
                issues=[],
            ),
        ]
    )

    with patch("app.api.ws_run.CritiqueNodeExecutor", return_value=mock_executor):
        await _run_critique_node(
            critique_spec={
                "agent_id": "c1",
                "agent_name": "Critique",
                "agent_type": "critique",
                "depends_on": ["a1", "a2"],
            },
            ordered_agents=ordered_agents,
            results=results,
            context={},
            send=AsyncMock(),
            rerun_agent=AsyncMock(),
        )

    assert results["c1"].status == "failed"
    assert results["c1"].output["critique_verdict"] == "NEEDS_FIX"


def test_ws_run_dispatches_critique_even_when_dependency_failed():
    pipeline_id = client.post("/api/pipelines", json={"objective": "Run critique after failure"}).json()["id"]

    db = SessionLocal()
    try:
        pipeline = db.query(PipelineORM).filter(PipelineORM.id == pipeline_id).first()
        pipeline.blueprint = {
            "agents": [
                {
                    "agent_id": "task_1",
                    "agent_name": "TaskOne",
                    "agent_type": "task",
                    "description": "Fails first",
                    "input_schema": {},
                    "output_schema": {},
                    "depends_on": [],
                },
                {
                    "agent_id": "critique_1",
                    "agent_name": "CritiqueOne",
                    "agent_type": "critique",
                    "description": "Critiques the failed task",
                    "depends_on": ["task_1"],
                },
            ]
        }
        db.commit()
    finally:
        db.close()

    run_id = client.post("/api/runs", json={"pipeline_id": pipeline_id, "inputs": {}}).json()["id"]
    critique_calls = []

    async def fake_execute(agent_spec, context, on_code_event=None):
        return AgentResult(
            agent_id=agent_spec["agent_id"],
            agent_name=agent_spec["agent_name"],
            status="failed",
            output={},
            error="boom",
            duration_ms=1,
        )

    async def fake_run_critique_node(critique_spec, ordered_agents, results, context, send, rerun_agent):
        critique_calls.append(critique_spec["agent_id"])
        result = AgentResult(
            agent_id=critique_spec["agent_id"],
            agent_name=critique_spec["agent_name"],
            status="completed",
            output={"critique_verdict": "APPROVED"},
            error=None,
            duration_ms=0,
        )
        results[critique_spec["agent_id"]] = result
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

    with (
        patch.object(settings, "gemini_api_key", "test-key"),
        patch.object(settings, "openai_api_key", ""),
        patch("app.api.ws_run.AgentExecutorAgent.execute", new=AsyncMock(side_effect=fake_execute)),
        patch("app.api.ws_run._run_critique_node", new=AsyncMock(side_effect=fake_run_critique_node)),
    ):
        with client.websocket_connect(f"/ws/run/{run_id}") as websocket:
            events = []
            for _ in range(20):
                event = websocket.receive_json()
                events.append(event)
                if event["type"] in {"RUN_COMPLETE", "ERROR"}:
                    break
            else:
                raise AssertionError("ws_run flow did not finish within 20 events")

    assert critique_calls == ["critique_1"]
    run_complete = next(event for event in events if event["type"] == "RUN_COMPLETE")
    result_ids = [result["agent_id"] for result in run_complete["results"]]
    assert result_ids == ["task_1", "critique_1"]
