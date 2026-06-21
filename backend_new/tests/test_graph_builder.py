import pytest
from app.services.graph_builder import GraphBuilder
from app.models import Agent, Edge


def test_add_agents_and_topological_sort():
    """Test adding agents and getting topological order."""
    builder = GraphBuilder()

    # Create agents
    agent1 = Agent(id="a1", execution_id="exec_1", agent_type="sub_agent", depth=0, task_description="Root", status="pending")
    agent2 = Agent(id="a2", execution_id="exec_1", agent_type="atomic_agent", depth=1, task_description="Task 1", status="pending")
    agent3 = Agent(id="a3", execution_id="exec_1", agent_type="atomic_agent", depth=1, task_description="Task 2", status="pending")

    builder.add_agent(agent1)
    builder.add_agent(agent2)
    builder.add_agent(agent3)

    # Add edges: a1 -> a2, a1 -> a3
    edge1 = Edge(id="e1", execution_id="exec_1", from_agent_id="a1", to_agent_id="a2")
    edge2 = Edge(id="e2", execution_id="exec_1", from_agent_id="a1", to_agent_id="a3")

    builder.add_edge(edge1)
    builder.add_edge(edge2)

    # Get topological order
    order = builder.topological_sort()

    # a1 must come before a2 and a3
    assert order.index("a1") < order.index("a2")
    assert order.index("a1") < order.index("a3")


def test_cycle_detection():
    """Test that cycles are detected."""
    builder = GraphBuilder()

    agent1 = Agent(id="a1", execution_id="exec_1", agent_type="atomic_agent", depth=1, task_description="Task 1", status="pending")
    agent2 = Agent(id="a2", execution_id="exec_1", agent_type="atomic_agent", depth=1, task_description="Task 2", status="pending")

    builder.add_agent(agent1)
    builder.add_agent(agent2)

    # Create cycle: a1 -> a2 -> a1
    edge1 = Edge(id="e1", execution_id="exec_1", from_agent_id="a1", to_agent_id="a2")
    edge2 = Edge(id="e2", execution_id="exec_1", from_agent_id="a2", to_agent_id="a1")

    builder.add_edge(edge1)
    builder.add_edge(edge2)

    # Should detect cycle
    assert builder.validate_no_cycles() is False


def test_max_recursion_depth_constraint():
    """Test that maximum recursion depth constraint is enforced (max depth = 5)."""
    builder = GraphBuilder()

    # Agent at depth 5 should be allowed
    agent_valid = Agent(
        id="a_valid",
        execution_id="exec_1",
        agent_type="atomic_agent",
        depth=5,
        task_description="At max depth",
        status="pending"
    )
    builder.add_agent(agent_valid)
    assert "a_valid" in builder.agents

    # Agent at depth 6 should raise ValueError
    agent_invalid = Agent(
        id="a_invalid",
        execution_id="exec_1",
        agent_type="atomic_agent",
        depth=6,
        task_description="Exceeds max depth",
        status="pending"
    )
    with pytest.raises(ValueError) as exc_info:
        builder.add_agent(agent_invalid)
    assert "exceeds maximum recursion depth" in str(exc_info.value)


def test_max_children_per_agent_constraint():
    """Test that maximum children per agent constraint is enforced (max = 10)."""
    builder = GraphBuilder()

    # Create parent agent and 10 child agents
    parent = Agent(
        id="parent",
        execution_id="exec_1",
        agent_type="sub_agent",
        depth=0,
        task_description="Parent",
        status="pending"
    )
    builder.add_agent(parent)

    # Add 10 child agents and edges (should all succeed)
    for i in range(10):
        child = Agent(
            id=f"child_{i}",
            execution_id="exec_1",
            agent_type="atomic_agent",
            depth=1,
            task_description=f"Child {i}",
            status="pending"
        )
        builder.add_agent(child)

        edge = Edge(
            id=f"edge_{i}",
            execution_id="exec_1",
            from_agent_id="parent",
            to_agent_id=f"child_{i}"
        )
        builder.add_edge(edge)

    # Verify 10 children were added
    assert len(builder.adjacency["parent"]) == 10

    # Adding 11th child should raise ValueError
    child_11 = Agent(
        id="child_11",
        execution_id="exec_1",
        agent_type="atomic_agent",
        depth=1,
        task_description="Child 11",
        status="pending"
    )
    builder.add_agent(child_11)

    edge_11 = Edge(
        id="edge_11",
        execution_id="exec_1",
        from_agent_id="parent",
        to_agent_id="child_11"
    )

    with pytest.raises(ValueError) as exc_info:
        builder.add_edge(edge_11)
    assert "Cannot exceed maximum" in str(exc_info.value)
    assert "10 children" in str(exc_info.value)
