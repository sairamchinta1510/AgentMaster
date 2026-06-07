import pytest
from app.models.agent import AtomicAgent, AgentState, CritiqueResult, CritiqueVerdict
from app.models.dag import DAGNode, DAGEdge, DAGGraph
from app.models.session import ExecutionSession, Phase


def test_atomic_agent_default_state():
    a = AtomicAgent(agent_id="a1", agent_name="TestAgent", session_id="s1")
    assert a.state == AgentState.PENDING
    assert a.critique_iterations == 0


def test_critique_result_verdict():
    c = CritiqueResult(
        critique_id="c1",
        target_agent="a1",
        target_agent_name="TestAgent",
        phase="design_time",
        iteration=1,
        max_iterations=5,
        verdict=CritiqueVerdict.APPROVED,
        quality_score=9,
        errors_remaining=0,
    )
    assert c.verdict == CritiqueVerdict.APPROVED
    assert c.errors_remaining == 0


def test_dag_graph_add_node():
    g = DAGGraph(session_id="s1")
    node = DAGNode(node_id="n1", agent_id="a1", agent_name="TestAgent")
    g.add_node(node)
    assert "n1" in g.nodes


def test_dag_graph_edge():
    g = DAGGraph(session_id="s1")
    g.add_node(DAGNode(node_id="n1", agent_id="a1", agent_name="A1"))
    g.add_node(DAGNode(node_id="n2", agent_id="a2", agent_name="A2"))
    g.add_edge(DAGEdge(edge_id="e1", from_node="n1", to_node="n2"))
    assert len(g.edges) == 1


def test_session_initial_phase():
    s = ExecutionSession(session_id="s1", objective="test objective")
    assert s.phase == Phase.DESIGN
