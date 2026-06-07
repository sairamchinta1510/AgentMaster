import pytest
from app.engine.lifecycle import AgentLifecycle
from app.models.agent import AgentState


def test_initial_state():
    lc = AgentLifecycle(agent_id="a1")
    assert lc.state == AgentState.PENDING


def test_transition_to_specifying():
    lc = AgentLifecycle(agent_id="a1")
    lc.transition(AgentState.SPECIFYING)
    assert lc.state == AgentState.SPECIFYING


def test_invalid_transition_raises():
    lc = AgentLifecycle(agent_id="a1")
    with pytest.raises(ValueError, match="Invalid transition"):
        lc.transition(AgentState.COMPLETED)


def test_critique_iteration_increment():
    lc = AgentLifecycle(agent_id="a1")
    lc.transition(AgentState.SPECIFYING)
    lc.transition(AgentState.DESIGN_CRITIQUE_1)
    lc.increment_critique()
    assert lc.critique_count == 1


def test_max_iterations_reached():
    lc = AgentLifecycle(agent_id="a1")
    lc.state = AgentState.DESIGN_CRITIQUE_5
    lc.critique_count = 5
    assert lc.max_iterations_reached() is True


def test_next_critique_state():
    lc = AgentLifecycle(agent_id="a1")
    assert lc.next_critique_state() == AgentState.DESIGN_CRITIQUE_1
    lc.critique_count = 1
    assert lc.next_critique_state() == AgentState.DESIGN_CRITIQUE_2
