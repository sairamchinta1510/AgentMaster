import pytest
from app.models.dag import DAGGraph, DAGNode, DAGEdge
from app.engine.dag import DAGEngine


def test_ready_nodes_no_deps():
    g = DAGGraph(session_id="s1")
    g.add_node(DAGNode(node_id="n1", agent_id="a1", agent_name="A1"))
    g.add_node(DAGNode(node_id="n2", agent_id="a2", agent_name="A2"))
    engine = DAGEngine(g)
    ready = engine.get_ready_nodes(completed=set())
    assert {n.node_id for n in ready} == {"n1", "n2"}


def test_ready_nodes_with_dep():
    g = DAGGraph(session_id="s1")
    g.add_node(DAGNode(node_id="n1", agent_id="a1", agent_name="A1"))
    g.add_node(DAGNode(node_id="n2", agent_id="a2", agent_name="A2"))
    g.add_edge(DAGEdge(edge_id="e1", from_node="n1", to_node="n2"))
    engine = DAGEngine(g)
    ready = engine.get_ready_nodes(completed=set())
    assert len(ready) == 1
    assert ready[0].node_id == "n1"


def test_ready_nodes_after_complete():
    g = DAGGraph(session_id="s1")
    g.add_node(DAGNode(node_id="n1", agent_id="a1", agent_name="A1"))
    g.add_node(DAGNode(node_id="n2", agent_id="a2", agent_name="A2"))
    g.add_edge(DAGEdge(edge_id="e1", from_node="n1", to_node="n2"))
    engine = DAGEngine(g)
    ready = engine.get_ready_nodes(completed={"n1"})
    assert ready[0].node_id == "n2"


def test_inject_node():
    g = DAGGraph(session_id="s1")
    engine = DAGEngine(g)
    engine.inject_node(
        DAGNode(node_id="n_new", agent_id="a_new", agent_name="NewAgent"),
        after_node_id=None,
    )
    assert "n_new" in g.nodes


def test_is_complete():
    g = DAGGraph(session_id="s1")
    g.add_node(DAGNode(node_id="n1", agent_id="a1", agent_name="A1"))
    engine = DAGEngine(g)
    assert not engine.is_complete(set())
    assert engine.is_complete({"n1"})
