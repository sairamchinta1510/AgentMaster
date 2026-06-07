import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.agent_critique import AgentCritiqueAgent, run_critique_loop
from app.models.agent import CritiqueVerdict, AtomicAgent


@pytest.mark.asyncio
async def test_critique_returns_approved_on_first_iteration():
    agent = AtomicAgent(
        agent_id="a1",
        agent_name="TestAgent",
        session_id="s1",
        input_schema={"data": {"type": "string"}},
        output_schema={"result": {"type": "string"}},
        description="Reads a single string value",
    )
    mock_response = {
        "critique_id": "a1_critique_iter_1",
        "target_agent": "a1",
        "target_agent_name": "TestAgent",
        "phase": "design_time",
        "iteration": 1,
        "max_iterations": 5,
        "verdict": "APPROVED",
        "quality_score": 9.0,
        "errors_remaining": 0,
        "issues": [],
        "approved_aspects": ["Single action", "Full schema"],
        "improvements_made_this_iteration": [],
        "remaining_errors": [],
        "suggested_new_agents": [],
        "missing_user_inputs": [],
    }
    critique_agent = AgentCritiqueAgent(api_key="fake")
    with patch.object(critique_agent, "_call_llm", new_callable=AsyncMock, return_value=mock_response):
        result = await critique_agent.critique(agent, phase="design_time", iteration=1)
    assert result.verdict == CritiqueVerdict.APPROVED
    assert result.errors_remaining == 0


@pytest.mark.asyncio
async def test_critique_loop_escalates_after_5_iterations():
    agent = AtomicAgent(
        agent_id="a2",
        agent_name="BrokenAgent",
        session_id="s1",
        description="Broken agent",
    )
    needs_revision = {
        "critique_id": "a2_critique_iter_1",
        "target_agent": "a2",
        "target_agent_name": "BrokenAgent",
        "phase": "design_time",
        "iteration": 1,
        "max_iterations": 5,
        "verdict": "NEEDS_REVISION",
        "quality_score": 3.0,
        "errors_remaining": 2,
        "issues": [
            {
                "issue_id": "I1",
                "severity": "critical",
                "category": "atomicity",
                "description": "Does too much",
                "impact": "Bad",
                "recommendation": "Split it",
                "effort_estimate": "low",
                "auto_fixable": True,
            }
        ],
        "approved_aspects": [],
        "improvements_made_this_iteration": [],
        "remaining_errors": ["atomicity violation"],
        "suggested_new_agents": [],
        "missing_user_inputs": [],
    }
    critique_agent = AgentCritiqueAgent(api_key="fake")
    producer_agent = MagicMock()
    producer_agent.revise = AsyncMock(return_value=agent)

    with patch.object(critique_agent, "_call_llm", new_callable=AsyncMock, return_value=needs_revision):
        result, final_agent, iterations = await run_critique_loop(
            agent, critique_agent, producer_agent, phase="design_time"
        )

    assert iterations == 5
    assert result.verdict in [
        CritiqueVerdict.NEEDS_REVISION,
        CritiqueVerdict.ESCALATE_AUTO_FIX,
        CritiqueVerdict.ESCALATE_RETHINK,
        CritiqueVerdict.ESCALATE_USER,
    ]


@pytest.mark.asyncio
async def test_critique_loop_exits_on_approval():
    agent = AtomicAgent(
        agent_id="a3",
        agent_name="GoodAgent",
        session_id="s1",
        description="Does one thing",
    )
    approved_response = {
        "critique_id": "a3_critique_iter_1",
        "target_agent": "a3",
        "target_agent_name": "GoodAgent",
        "phase": "design_time",
        "iteration": 1,
        "max_iterations": 5,
        "verdict": "APPROVED",
        "quality_score": 8.5,
        "errors_remaining": 0,
        "issues": [],
        "approved_aspects": ["Atomic", "Fully documented"],
        "improvements_made_this_iteration": [],
        "remaining_errors": [],
        "suggested_new_agents": [],
        "missing_user_inputs": [],
    }
    critique_agent = AgentCritiqueAgent(api_key="fake")
    producer_agent = MagicMock()
    producer_agent.revise = AsyncMock(return_value=agent)

    with patch.object(critique_agent, "_call_llm", new_callable=AsyncMock, return_value=approved_response):
        result, final_agent, iterations = await run_critique_loop(
            agent, critique_agent, producer_agent, phase="design_time"
        )

    assert iterations == 1
    assert result.verdict == CritiqueVerdict.APPROVED
    assert final_agent.quality_score == 8.5
