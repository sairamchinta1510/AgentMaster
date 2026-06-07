# backend/tests/test_agent_executor.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.agents.agent_executor import AgentExecutorAgent


AGENT_SPEC = {
    "agent_id": "agent_001",
    "agent_name": "TestAgent",
    "description": "Test agent",
    "input_schema": {"query": {"type": "string"}},
    "output_schema": {"result": {"type": "string"}},
}


@pytest.mark.asyncio
async def test_no_code_needed_path():
    executor = AgentExecutorAgent()
    plan_response = MagicMock()
    plan_response.choices[0].message.content = '{"action": "NO_CODE_NEEDED", "output": {"result": "hello"}}'

    with patch.object(executor.client.chat.completions, "create", new=AsyncMock(return_value=plan_response)):
        result = await executor.execute(AGENT_SPEC, {"query": "hi"})

    assert result.status == "completed"
    assert result.output["result"] == "hello"


@pytest.mark.asyncio
async def test_execute_code_path():
    executor = AgentExecutorAgent()
    plan_response = MagicMock()
    plan_response.choices[0].message.content = (
        '{"action": "EXECUTE_CODE", "code": "print(\'test output\')", "credential_keys": []}'
    )
    synth_response = MagicMock()
    synth_response.choices[0].message.content = '{"result": "test output"}'

    responses = [plan_response, synth_response]
    call_count = 0

    async def mock_create(**kwargs):
        nonlocal call_count
        r = responses[call_count]
        call_count += 1
        return r

    with patch.object(executor.client.chat.completions, "create", new=mock_create), \
         patch("app.agents.agent_executor.execute_python_code", new=AsyncMock(return_value=("test output\n", "", 0))):
        result = await executor.execute(AGENT_SPEC, {})

    assert result.status == "completed"
    assert result.output["result"] == "test output"
    assert "_code" in result.output


@pytest.mark.asyncio
async def test_code_event_callback_called():
    executor = AgentExecutorAgent()
    plan_response = MagicMock()
    plan_response.choices[0].message.content = '{"action": "NO_CODE_NEEDED", "output": {"result": "x"}}'
    phases = []

    async def on_event(agent_id, phase, preview):
        phases.append(phase)

    with patch.object(executor.client.chat.completions, "create", new=AsyncMock(return_value=plan_response)):
        await executor.execute(AGENT_SPEC, {}, on_code_event=on_event)

    assert "planning" in phases
    assert "fallback" in phases


@pytest.mark.asyncio
async def test_invalid_action_raises():
    executor = AgentExecutorAgent()
    plan_response = MagicMock()
    plan_response.choices[0].message.content = '{"action": "UNKNOWN_ACTION"}'

    with patch.object(executor.client.chat.completions, "create", new=AsyncMock(return_value=plan_response)):
        result = await executor.execute(AGENT_SPEC, {})

    assert result.status == "failed"
    assert "unknown action" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_retries_on_exec_failure_and_succeeds():
    """If code fails on first execution, agent re-plans with error context and succeeds."""
    executor = AgentExecutorAgent()

    plan_fail = MagicMock()
    plan_fail.choices[0].message.content = (
        '{"action": "EXECUTE_CODE", "code": "raise RuntimeError(\'oops\')", "credential_keys": []}'
    )
    plan_ok = MagicMock()
    plan_ok.choices[0].message.content = (
        '{"action": "EXECUTE_CODE", "code": "print(\'fixed\')", "credential_keys": []}'
    )
    synth = MagicMock()
    synth.choices[0].message.content = '{"result": "fixed"}'

    responses = [plan_fail, plan_ok, synth]
    call_count = 0

    async def mock_create(**kwargs):
        nonlocal call_count
        r = responses[call_count]
        call_count += 1
        return r

    exec_results = [("", "RuntimeError: oops", 1), ("fixed\n", "", 0)]
    exec_count = 0

    async def mock_exec(code, env):
        nonlocal exec_count
        r = exec_results[exec_count]
        exec_count += 1
        return r

    with patch.object(executor.client.chat.completions, "create", new=mock_create), \
         patch("app.agents.agent_executor.execute_python_code", new=mock_exec):
        result = await executor.execute(AGENT_SPEC, {})

    assert result.status == "completed"
    assert result.output.get("result") == "fixed"


@pytest.mark.asyncio
async def test_fails_after_max_retries_exhausted():
    """Agent gives up and returns failed after all retry attempts are exhausted."""
    executor = AgentExecutorAgent()

    plan_response = MagicMock()
    plan_response.choices[0].message.content = (
        '{"action": "EXECUTE_CODE", "code": "raise RuntimeError(\'always fails\')", "credential_keys": []}'
    )

    with patch.object(executor.client.chat.completions, "create", new=AsyncMock(return_value=plan_response)), \
         patch("app.agents.agent_executor.execute_python_code", new=AsyncMock(return_value=("", "RuntimeError: always fails", 1))):
        result = await executor.execute(AGENT_SPEC, {})

    assert result.status == "failed"
    assert result.error is not None
