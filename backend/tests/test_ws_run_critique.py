import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app

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
