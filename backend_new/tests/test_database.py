import uuid
from datetime import datetime
from app.models import Execution, Agent, Edge, Critique, ToolExecution, AgentTemplate


def test_create_execution(db_session):
    """Test creating an Execution record."""
    exec_id = str(uuid.uuid4())
    execution = Execution(
        id=exec_id,
        objective="Test objective",
        domain="Test Domain",
        status="planning",
        config={"max_recursion_depth": 5}
    )
    db_session.add(execution)
    db_session.commit()

    retrieved = db_session.query(Execution).filter_by(id=exec_id).first()
    assert retrieved is not None
    assert retrieved.objective == "Test objective"
    assert retrieved.domain == "Test Domain"
    assert retrieved.status == "planning"
    assert retrieved.config["max_recursion_depth"] == 5


def test_create_agent(db_session):
    """Test creating an Agent record."""
    exec_id = str(uuid.uuid4())
    execution = Execution(id=exec_id, objective="Test", domain="Test", status="planning")
    db_session.add(execution)
    db_session.commit()

    agent_id = str(uuid.uuid4())
    agent = Agent(
        id=agent_id,
        execution_id=exec_id,
        parent_id=None,
        agent_type="sub_agent",
        depth=0,
        task_description="Root task",
        status="pending",
        timeout_seconds=300
    )
    db_session.add(agent)
    db_session.commit()

    retrieved = db_session.query(Agent).filter_by(id=agent_id).first()
    assert retrieved is not None
    assert retrieved.agent_type == "sub_agent"
    assert retrieved.depth == 0
    assert retrieved.status == "pending"


def test_create_edge(db_session):
    """Test creating an Edge record."""
    exec_id = str(uuid.uuid4())
    execution = Execution(id=exec_id, objective="Test", domain="Test", status="planning")
    db_session.add(execution)

    agent1_id = str(uuid.uuid4())
    agent2_id = str(uuid.uuid4())
    agent1 = Agent(id=agent1_id, execution_id=exec_id, agent_type="sub_agent", depth=0, task_description="Task 1", status="pending")
    agent2 = Agent(id=agent2_id, execution_id=exec_id, agent_type="atomic_agent", depth=1, task_description="Task 2", status="pending")
    db_session.add_all([agent1, agent2])
    db_session.commit()

    edge_id = str(uuid.uuid4())
    edge = Edge(
        id=edge_id,
        execution_id=exec_id,
        from_agent_id=agent1_id,
        to_agent_id=agent2_id,
        data_description="Output from agent1"
    )
    db_session.add(edge)
    db_session.commit()

    retrieved = db_session.query(Edge).filter_by(id=edge_id).first()
    assert retrieved is not None
    assert retrieved.from_agent_id == agent1_id
    assert retrieved.to_agent_id == agent2_id


def test_create_critique(db_session):
    """Test creating a Critique record."""
    exec_id = str(uuid.uuid4())
    execution = Execution(id=exec_id, objective="Test", domain="Test", status="running")
    agent_id = str(uuid.uuid4())
    agent = Agent(id=agent_id, execution_id=exec_id, agent_type="atomic_agent", depth=1, task_description="Test", status="critique_phase")
    db_session.add_all([execution, agent])
    db_session.commit()

    critique_id = str(uuid.uuid4())
    critique = Critique(
        id=critique_id,
        agent_id=agent_id,
        round_number=1,
        critique_type="factual_verification",
        verdict="passed",
        reasoning="All facts verified",
        unsupported_claims=[]
    )
    db_session.add(critique)
    db_session.commit()

    retrieved = db_session.query(Critique).filter_by(id=critique_id).first()
    assert retrieved is not None
    assert retrieved.round_number == 1
    assert retrieved.verdict == "passed"


def test_to_dict_methods(db_session):
    """Test that all models have working to_dict() methods."""
    exec_id = str(uuid.uuid4())
    execution = Execution(id=exec_id, objective="Test", domain="Test", status="planning")
    db_session.add(execution)
    db_session.commit()

    exec_dict = execution.to_dict()
    assert exec_dict["id"] == exec_id
    assert exec_dict["objective"] == "Test"
    assert "created_at" in exec_dict
