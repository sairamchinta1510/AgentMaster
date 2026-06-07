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

    with patch.object(executor.client.chat.completions, "create", new=mock_create):
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
