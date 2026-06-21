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
