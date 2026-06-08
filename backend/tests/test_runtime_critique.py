import pytest
from unittest.mock import AsyncMock, patch

from app.agents.runtime_critique import CritiqueLoopResult, CritiqueNodeExecutor
from app.prompts.critique_runtime import build_design_critique_prompt, build_run_critique_prompt


def test_design_critique_prompt_contains_agent_description():
    prompt = build_design_critique_prompt(
        agent_name="CloneRepository",
        agent_description="Clones a git repository to a local path",
        input_schema={"clone_url": {"type": "string"}},
        output_schema={"repository_path": {"type": "string"}},
    )
    assert "CloneRepository" in prompt
    assert "git" in prompt.lower() or "clone" in prompt.lower()
    assert "industry" in prompt.lower() or "standard" in prompt.lower()


def test_run_critique_prompt_contains_execution_results():
    prompt = build_run_critique_prompt(
        agent_name="IdentifyLogStorage",
        agent_description="Identifies the log storage mechanism",
        input_schema={"repository_path": {"type": "string"}},
        output_schema={"log_storage_mechanism": {"type": "string"}},
        actual_inputs={"REPOSITORY_PATH": "/tmp/tmpabc"},
        code="import os\npath = os.environ['REPOSITORY_PATH']",
        stdout='{"log_storage_mechanism": "file"}',
        stderr="",
        returncode=0,
    )
    assert "IdentifyLogStorage" in prompt
    assert "/tmp/tmpabc" in prompt
    assert "APPROVED" in prompt
    assert "NEEDS_FIX" in prompt


def test_run_critique_prompt_flags_output_schema_as_env_var():
    prompt = build_run_critique_prompt(
        agent_name="TestAgent",
        agent_description="Detects log events",
        input_schema={"repository_path": {"type": "string"}},
        output_schema={"detected_log_event": {"type": "string"}},
        actual_inputs={"REPOSITORY_PATH": "/tmp/repo"},
        code="import os\nevent = os.environ['DETECTED_LOG_EVENT']",
        stdout="",
        stderr="KeyError: 'DETECTED_LOG_EVENT'",
        returncode=1,
    )
    assert "output" in prompt.lower()
    assert "input" in prompt.lower()
    assert "DETECTED_LOG_EVENT" in prompt


# ── CritiqueNodeExecutor ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_critique_approves_and_returns_after_min_iterations():
    """Approved output should still run min_iterations times."""
    executor = CritiqueNodeExecutor(api_key="fake", model="gemini")
    approved = {"verdict": "APPROVED", "quality_score": 9.0, "issues": [], "fix_instructions": ""}

    with patch.object(executor, "_call_critique_llm", new=AsyncMock(return_value=approved)):
        result = await executor.run_design_critique(
            agent_spec={
                "agent_id": "a1",
                "agent_name": "CloneRepo",
                "description": "Clones a git repo",
                "input_schema": {"clone_url": {"type": "string"}},
                "output_schema": {"repository_path": {"type": "string"}},
            },
            min_iterations=3,
            max_iterations=5,
        )

    assert result.verdict == "APPROVED"
    assert result.iterations == 3


@pytest.mark.asyncio
async def test_critique_needs_fix_calls_on_fix_callback():
    """NEEDS_FIX should invoke on_fix_needed callback with instructions."""
    executor = CritiqueNodeExecutor(api_key="fake", model="gemini")
    needs_fix = {
        "verdict": "NEEDS_FIX",
        "quality_score": 3.0,
        "issues": ["Output field used as input env var"],
        "fix_instructions": "Remove os.environ['DETECTED_LOG_EVENT'] — produce that field instead",
    }
    approved = {"verdict": "APPROVED", "quality_score": 9.0, "issues": [], "fix_instructions": ""}

    responses = [needs_fix, needs_fix, approved, approved, approved]
    call_count = 0
    fix_calls = []

    async def mock_llm(*args, **kwargs):
        nonlocal call_count
        response = responses[call_count]
        call_count += 1
        return response

    async def on_fix(instructions: str, iteration: int):
        fix_calls.append((instructions, iteration))

    with patch.object(executor, "_call_critique_llm", new=mock_llm):
        result = await executor.run_design_critique(
            agent_spec={
                "agent_id": "a1",
                "agent_name": "DetectLog",
                "description": "Detects log events",
                "input_schema": {"repository_path": {"type": "string"}},
                "output_schema": {"detected_log_event": {"type": "string"}},
            },
            min_iterations=3,
            max_iterations=5,
            on_fix_needed=on_fix,
        )

    assert len(fix_calls) == 2
    assert "DETECTED_LOG_EVENT" in fix_calls[0][0]
    assert result.verdict == "APPROVED"


@pytest.mark.asyncio
async def test_critique_fails_after_max_iterations():
    """If NEEDS_FIX persists through max_iterations, result is NEEDS_FIX."""
    executor = CritiqueNodeExecutor(api_key="fake", model="gemini")
    needs_fix = {
        "verdict": "NEEDS_FIX",
        "quality_score": 2.0,
        "issues": ["Always broken"],
        "fix_instructions": "Fix it",
    }

    with patch.object(executor, "_call_critique_llm", new=AsyncMock(return_value=needs_fix)):
        result = await executor.run_design_critique(
            agent_spec={
                "agent_id": "a1",
                "agent_name": "BrokenAgent",
                "description": "Always broken",
                "input_schema": {},
                "output_schema": {},
            },
            min_iterations=3,
            max_iterations=5,
        )

    assert result.verdict == "NEEDS_FIX"
    assert result.iterations == 5


@pytest.mark.asyncio
async def test_run_critique_passes_execution_context_to_llm():
    """run_exec_critique passes code/stdout/stderr to the LLM."""
    executor = CritiqueNodeExecutor(api_key="fake", model="gemini")
    approved = {"verdict": "APPROVED", "quality_score": 8.0, "issues": [], "fix_instructions": ""}
    captured_prompts = []

    async def mock_llm(prompt: str):
        captured_prompts.append(prompt)
        return approved

    with patch.object(executor, "_call_critique_llm", new=mock_llm):
        await executor.run_exec_critique(
            agent_spec={
                "agent_id": "a1",
                "agent_name": "Identify",
                "description": "Identifies log storage",
                "input_schema": {"repository_path": {"type": "string"}},
                "output_schema": {"log_storage_mechanism": {"type": "string"}},
            },
            actual_inputs={"REPOSITORY_PATH": "/tmp/tmpabc"},
            code="import os\npath = os.environ['REPOSITORY_PATH']",
            stdout='{"log_storage_mechanism": "file"}',
            stderr="",
            returncode=0,
            min_iterations=3,
            max_iterations=5,
        )

    assert any("/tmp/tmpabc" in prompt for prompt in captured_prompts)
