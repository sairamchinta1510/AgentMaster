import pytest
import uuid
from app.agents.orchestrator import AgentMaster
from app.models import Execution, Agent


def test_orchestrator_creates_root_agent(db_session):
    """Test that AgentMaster creates a root Sub-Agent."""
    exec_id = str(uuid.uuid4())

    execution = Execution(
        id=exec_id,
        objective="Create a presentation on AI",
        domain="Create PPT",
        status="planning"
    )
    db_session.add(execution)
    db_session.commit()

    orchestrator = AgentMaster(
        execution_id=exec_id,
        objective="Create a presentation on AI",
        domain="Create PPT",
        db_session=db_session
    )

    result = orchestrator.plan()

    assert "root_agent_id" in result
    assert "plan_summary" in result

    # Check that root agent was created in database
    root_agent = db_session.query(Agent).filter_by(id=result["root_agent_id"]).first()
    assert root_agent is not None
    assert root_agent.agent_type == "sub_agent"
    assert root_agent.depth == 0
    assert root_agent.execution_id == exec_id


def test_orchestrator_handles_any_domain(db_session):
    """Test that AgentMaster accepts any user-defined domain."""
    exec_id = str(uuid.uuid4())

    execution = Execution(
        id=exec_id,
        objective="Book tickets to Paris",
        domain="Travel Planning",  # User-defined domain
        status="planning"
    )
    db_session.add(execution)
    db_session.commit()

    orchestrator = AgentMaster(
        execution_id=exec_id,
        objective="Book tickets to Paris",
        domain="Travel Planning",
        db_session=db_session
    )

    result = orchestrator.plan()

    assert "root_agent_id" in result
    # Should not reject based on domain
