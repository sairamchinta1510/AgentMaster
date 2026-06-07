import pytest
from app.library.agent_library import AgentLibrary
from app.models.dag import DAGGraph, DAGNode


@pytest.fixture
def library(tmp_path):
    db_url = f"sqlite:///{tmp_path}/test.db"
    return AgentLibrary(db_url=db_url)


def test_save_and_retrieve_flow(library):
    graph = DAGGraph(session_id="s1")
    graph.add_node(DAGNode(node_id="n1", agent_id="a1", agent_name="Analyzer"))
    library.save_flow(
        session_id="s1",
        name="Test Flow",
        objective="Analyze a GitHub repo",
        domain="DevOps",
        graph=graph,
        quality_score=8.5,
    )
    results = library.search("GitHub repo")
    assert len(results) >= 1
    assert results[0]["name"] == "Test Flow"


def test_search_returns_empty_for_no_match(library):
    results = library.search("completely unrelated query xyz123abc")
    assert isinstance(results, list)
    assert len(results) == 0


def test_get_by_id(library):
    graph = DAGGraph(session_id="s2")
    lib_id = library.save_flow(
        session_id="s2",
        name="Finance Flow",
        objective="Audit financial transactions for compliance",
        domain="Finance",
        graph=graph,
        quality_score=9.0,
    )
    flow = library.get_by_id(lib_id)
    assert flow is not None
    assert flow["name"] == "Finance Flow"


def test_list_all(library):
    graph = DAGGraph(session_id="s3")
    library.save_flow(
        session_id="s3",
        name="DevOps Flow",
        objective="Monitor logs",
        domain="DevOps",
        graph=graph,
        quality_score=7.0,
    )
    all_flows = library.list_all()
    assert len(all_flows) >= 1
    assert all("name" in f for f in all_flows)
