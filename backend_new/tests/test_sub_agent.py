import pytest
import uuid
from app.agents.sub_agent import SubAgent
from app.models import Agent


def test_sub_agent_simple_task_decomposition(db_session):
    """Test SubAgent decomposes simple task into Atomic Agents."""
    agent_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())

    agent = Agent(
        id=agent_id,
        execution_id=exec_id,
        agent_type="sub_agent",
        depth=0,
        task_description="Echo hello world",
        status="pending"
    )
    db_session.add(agent)
    db_session.commit()

    sub = SubAgent(
        agent_id=agent_id,
        task_description="Echo hello world",
        input_data={},
        depth=0,
        domain="Test Domain",
        db_session=db_session
    )

    result = sub.decompose()

    assert "complexity_score" in result
    assert result["complexity_score"] >= 3  # Minimum score
    assert result["complexity_score"] <= 9  # Maximum score
    assert "children" in result
    assert len(result["children"]) > 0
    assert "reasoning" in result


def test_sub_agent_respects_max_depth(db_session):
    """Test that SubAgent doesn't spawn Sub-Agents at max depth."""
    from app.config import settings

    agent_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())

    agent = Agent(
        id=agent_id,
        execution_id=exec_id,
        agent_type="sub_agent",
        depth=settings.max_recursion_depth,  # At max depth
        task_description="Complex task",
        status="pending"
    )
    db_session.add(agent)
    db_session.commit()

    sub = SubAgent(
        agent_id=agent_id,
        task_description="Complex task with many steps",
        input_data={},
        depth=settings.max_recursion_depth,
        domain="Test",
        db_session=db_session
    )

    result = sub.decompose()

    # At max depth, should only spawn Atomic Agents
    for child in result["children"]:
        assert child["agent_type"] == "atomic_agent"
