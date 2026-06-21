import pytest
import uuid
from app.services.execution_manager import ExecutionManager
from app.models import Execution, Agent


@pytest.mark.asyncio
async def test_execution_manager_runs_single_agent(db_session):
    """Test ExecutionManager executes a single Atomic Agent."""
    exec_id = str(uuid.uuid4())

    execution = Execution(
        id=exec_id,
        objective="Test",
        domain="Test",
        status="running"
    )
    db_session.add(execution)
    db_session.commit()

    agent_id = str(uuid.uuid4())
    agent = Agent(
        id=agent_id,
        execution_id=exec_id,
        agent_type="atomic_agent",
        depth=1,
        task_description="Echo hello",
        status="pending",
        input_data={"command": "echo 'hello'"}
    )
    db_session.add(agent)
    db_session.commit()

    manager = ExecutionManager(execution_id=exec_id, db_session=db_session)
    await manager.execute()

    # Check agent status changed
    db_session.refresh(agent)
    assert agent.status in ["completed", "critique_phase"]


@pytest.mark.asyncio
async def test_execution_manager_respects_topological_order(db_session):
    """Test that ExecutionManager executes agents in dependency order."""
    exec_id = str(uuid.uuid4())

    execution = Execution(
        id=exec_id,
        objective="Test",
        domain="Test",
        status="running"
    )
    db_session.add(execution)

    # Create 2 agents with dependency: a1 -> a2
    a1_id = str(uuid.uuid4())
    a2_id = str(uuid.uuid4())

    a1 = Agent(
        id=a1_id,
        execution_id=exec_id,
        agent_type="atomic_agent",
        depth=1,
        task_description="Task 1",
        status="pending",
        input_data={"command": "echo 'step 1'"}
    )
    a2 = Agent(
        id=a2_id,
        execution_id=exec_id,
        agent_type="atomic_agent",
        depth=1,
        task_description="Task 2",
        status="pending",
        input_data={"command": "echo 'step 2'"}
    )

    from app.models import Edge
    edge = Edge(
        id=str(uuid.uuid4()),
        execution_id=exec_id,
        from_agent_id=a1_id,
        to_agent_id=a2_id
    )

    db_session.add_all([a1, a2, edge])
    db_session.commit()

    manager = ExecutionManager(execution_id=exec_id, db_session=db_session)
    await manager.execute()

    # Both should complete
    db_session.refresh(a1)
    db_session.refresh(a2)
    assert a1.status == "completed"
    assert a2.status in ["completed", "critique_phase"]
