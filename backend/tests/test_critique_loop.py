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


@pytest.mark.asyncio
async def test_critique_loop_decomposes_on_persistent_atomicity():
    """On iteration 2+, atomicity issue + suggested_new_agents → decompose into 2 agents."""
    agent = AtomicAgent(
        agent_id="orig",
        agent_name="MultiAgent",
        session_id="s1",
        description="Clones repo and analyzes logs",
    )

    atomicity_issue = {
        "issue_id": "ISS-001",
        "severity": "critical",
        "category": "atomicity",
        "description": "Does two things",
        "impact": "Violates Law 1",
        "recommendation": "Split into two agents",
        "effort_estimate": "medium",
        "auto_fixable": True,
    }

    critique_with_decomp = {
        "critique_id": "orig_critique_iter_1",
        "target_agent": "orig",
        "target_agent_name": "MultiAgent",
        "phase": "design_time",
        "iteration": 1,
        "max_iterations": 5,
        "verdict": "NEEDS_REVISION",
        "quality_score": 3.0,
        "errors_remaining": 1,
        "issues": [atomicity_issue],
        "approved_aspects": [],
        "improvements_made_this_iteration": [],
        "remaining_errors": ["atomicity"],
        "suggested_new_agents": [
            {
                "agent_name": "CloneRepoAgent",
                "description": "Clones a git repository to a local path",
                "input_schema": {"repo_url": {"type": "string", "required": True, "description": "URL"}},
                "output_schema": {"repo_path": {"type": "string", "description": "Local path"}},
            },
            {
                "agent_name": "AnalyzeLogsAgent",
                "description": "Analyzes log files in a given directory",
                "input_schema": {"repo_path": {"type": "string", "required": True, "description": "Path"}},
                "output_schema": {"log_summary": {"type": "string", "description": "Summary"}},
            },
        ],
        "missing_user_inputs": [],
    }

    sub_agent_1 = AtomicAgent(
        agent_id="orig_part_1",
        agent_name="CloneRepoAgent",
        session_id="s1",
        description="Clones a git repository to a local path",
    )
    sub_agent_2 = AtomicAgent(
        agent_id="orig_part_2",
        agent_name="AnalyzeLogsAgent",
        session_id="s1",
        description="Analyzes log files in a given directory",
    )

    critique_agent = AgentCritiqueAgent(api_key="fake")
    producer_agent = MagicMock()
    producer_agent.revise = AsyncMock(return_value=agent)
    producer_agent.produce = AsyncMock(side_effect=[sub_agent_1, sub_agent_2])

    with patch.object(critique_agent, "_call_llm", new_callable=AsyncMock, return_value=critique_with_decomp):
        with patch("app.agents.agent_critique.run_critique_loop") as mock_inner_loop:
            mock_inner_loop.side_effect = [
                (MagicMock(errors_remaining=0, verdict="APPROVED", quality_score=9.0), [sub_agent_1], 1),
                (MagicMock(errors_remaining=0, verdict="APPROVED", quality_score=9.0), [sub_agent_2], 1),
            ]
            result, agents, iterations = await run_critique_loop(
                agent, critique_agent, producer_agent, phase="design_time"
            )

    assert result.verdict == CritiqueVerdict.NEEDS_REVISION
    assert iterations == 2
    assert len(agents) == 2
    assert agents[0].agent_id == "orig_part_1"
    assert agents[1].agent_id == "orig_part_2"


@pytest.mark.asyncio
async def test_critique_loop_no_decomp_when_suggested_agents_empty():
    """Atomicity issue with empty suggested_new_agents → escalation, NOT decomposition."""
    agent = AtomicAgent(
        agent_id="a_esc",
        agent_name="EscalatedAgent",
        session_id="s1",
        description="Does too much but LLM gave no suggestions",
    )
    atomicity_no_suggestions = {
        "critique_id": "a_esc_critique_iter_1",
        "target_agent": "a_esc",
        "target_agent_name": "EscalatedAgent",
        "phase": "design_time",
        "iteration": 1,
        "max_iterations": 5,
        "verdict": "NEEDS_REVISION",
        "quality_score": 2.0,
        "errors_remaining": 1,
        "issues": [
            {
                "issue_id": "ISS-001",
                "severity": "critical",
                "category": "atomicity",
                "description": "Does two things",
                "impact": "Bad",
                "recommendation": "Split",
                "effort_estimate": "medium",
                "auto_fixable": False,
            }
        ],
        "approved_aspects": [],
        "improvements_made_this_iteration": [],
        "remaining_errors": ["atomicity"],
        "suggested_new_agents": [],
        "missing_user_inputs": [],
    }
    critique_agent = AgentCritiqueAgent(api_key="fake")
    producer_agent = MagicMock()
    producer_agent.revise = AsyncMock(return_value=agent)

    with patch.object(critique_agent, "_call_llm", new_callable=AsyncMock, return_value=atomicity_no_suggestions):
        result, agents, iterations = await run_critique_loop(
            agent, critique_agent, producer_agent, phase="design_time"
        )

    assert result.verdict == CritiqueVerdict.ESCALATE_AUTO_FIX
    assert len(agents) == 1
    assert iterations == 5


@pytest.mark.asyncio
async def test_critique_loop_single_agent_return_unchanged_on_approval():
    """Existing approval path still returns list of 1 agent."""
    agent = AtomicAgent(
        agent_id="good",
        agent_name="GoodAgent",
        session_id="s1",
        description="Does exactly one thing",
    )
    approved = {
        "critique_id": "good_critique_iter_1",
        "target_agent": "good",
        "target_agent_name": "GoodAgent",
        "phase": "design_time",
        "iteration": 1,
        "max_iterations": 5,
        "verdict": "APPROVED",
        "quality_score": 9.0,
        "errors_remaining": 0,
        "issues": [],
        "approved_aspects": [],
        "improvements_made_this_iteration": [],
        "remaining_errors": [],
        "suggested_new_agents": [],
        "missing_user_inputs": [],
    }
    critique_agent = AgentCritiqueAgent(api_key="fake")
    producer_agent = MagicMock()
    producer_agent.revise = AsyncMock(return_value=agent)

    with patch.object(critique_agent, "_call_llm", new_callable=AsyncMock, return_value=approved):
        result, agents, iterations = await run_critique_loop(
            agent, critique_agent, producer_agent, phase="design_time"
        )

    assert len(agents) == 1
    assert agents[0].agent_id == "good"
    assert result.verdict == CritiqueVerdict.APPROVED
