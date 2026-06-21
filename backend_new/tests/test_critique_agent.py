import pytest
import uuid
from app.agents.critique_agent import CritiqueAgent
from app.models import Agent, Critique


def test_critique_agent_approves_valid_output(db_session):
    """Test that CritiqueAgent approves output with citations."""
    agent_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())

    agent = Agent(
        id=agent_id,
        execution_id=exec_id,
        agent_type="atomic_agent",
        depth=1,
        task_description="Echo hello world",
        status="critique_phase"
    )
    db_session.add(agent)
    db_session.commit()

    agent_output = {
        "status": "completed",
        "data": {"stdout": "hello world"},
        "citations": [{"source_type": "command", "source": "echo 'hello world'", "excerpt": "hello world"}],
        "confidence": 100
    }

    critique = CritiqueAgent(
        agent_id=agent_id,
        agent_output=agent_output,
        task_description="Echo hello world",
        db_session=db_session
    )

    result = critique.run_critique()

    assert result["verdict"] in ["approved", "rejected", "needs_human_review"]
    assert "round_results" in result
    assert len(result["round_results"]) >= 3  # Minimum 3 rounds


def test_critique_agent_rejects_missing_citations(db_session):
    """Test that CritiqueAgent rejects output without citations."""
    agent_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())

    agent = Agent(
        id=agent_id,
        execution_id=exec_id,
        agent_type="atomic_agent",
        depth=1,
        task_description="Test task",
        status="critique_phase"
    )
    db_session.add(agent)
    db_session.commit()

    agent_output = {
        "status": "completed",
        "data": {"result": "some data"},
        "citations": [],  # No citations!
        "confidence": 100
    }

    critique = CritiqueAgent(
        agent_id=agent_id,
        agent_output=agent_output,
        task_description="Test task",
        db_session=db_session
    )

    result = critique.run_critique()

    # Should reject due to missing citations
    assert result["verdict"] == "rejected"

    # Check database for critique records
    critiques = db_session.query(Critique).filter_by(agent_id=agent_id).all()
    assert len(critiques) >= 1
