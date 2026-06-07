from app.models.agent import AgentState

VALID_TRANSITIONS: dict[AgentState, list[AgentState]] = {
    AgentState.PENDING: [
        AgentState.LIBRARY_SEARCH, AgentState.INPUT_COLLECTION, AgentState.SPECIFYING
    ],
    AgentState.LIBRARY_SEARCH: [AgentState.SPECIFYING, AgentState.INPUT_COLLECTION],
    AgentState.INPUT_COLLECTION: [AgentState.SPECIFYING],
    AgentState.SPECIFYING: [AgentState.DESIGN_CRITIQUE_1],
    AgentState.DESIGN_CRITIQUE_1: [
        AgentState.APPROVED, AgentState.REVISING_SPEC, AgentState.DESIGN_CRITIQUE_2
    ],
    AgentState.REVISING_SPEC: [
        AgentState.DESIGN_CRITIQUE_2, AgentState.DESIGN_CRITIQUE_3,
        AgentState.DESIGN_CRITIQUE_4, AgentState.DESIGN_CRITIQUE_5,
        AgentState.DESIGN_CRITIQUE_1,
    ],
    AgentState.DESIGN_CRITIQUE_2: [
        AgentState.APPROVED, AgentState.REVISING_SPEC, AgentState.DESIGN_CRITIQUE_3
    ],
    AgentState.DESIGN_CRITIQUE_3: [
        AgentState.APPROVED, AgentState.REVISING_SPEC, AgentState.DESIGN_CRITIQUE_4
    ],
    AgentState.DESIGN_CRITIQUE_4: [
        AgentState.APPROVED, AgentState.REVISING_SPEC, AgentState.DESIGN_CRITIQUE_5
    ],
    AgentState.DESIGN_CRITIQUE_5: [
        AgentState.APPROVED, AgentState.AUTO_FIX, AgentState.RETHINK, AgentState.USER_ESCALATED
    ],
    AgentState.AUTO_FIX: [AgentState.APPROVED, AgentState.RETHINK, AgentState.USER_ESCALATED],
    AgentState.RETHINK: [AgentState.SPECIFYING, AgentState.USER_ESCALATED],
    AgentState.APPROVED: [AgentState.SIMULATING, AgentState.EXECUTING],
    AgentState.SIMULATING: [AgentState.VALIDATED, AgentState.AUTO_FIX, AgentState.RETHINK],
    AgentState.VALIDATED: [AgentState.EXECUTING],
    AgentState.EXECUTING: [
        AgentState.COMPLETED, AgentState.AUTO_FIX, AgentState.RETHINK,
        AgentState.FAILED_ESCALATED
    ],
    AgentState.COMPLETED: [],
    AgentState.FAILED_ESCALATED: [],
    AgentState.USER_ESCALATED: [AgentState.SPECIFYING, AgentState.SKIPPED],
    AgentState.SKIPPED: [],
}

CRITIQUE_STATES = [
    AgentState.DESIGN_CRITIQUE_1,
    AgentState.DESIGN_CRITIQUE_2,
    AgentState.DESIGN_CRITIQUE_3,
    AgentState.DESIGN_CRITIQUE_4,
    AgentState.DESIGN_CRITIQUE_5,
]


class AgentLifecycle:
    def __init__(self, agent_id: str, max_iterations: int = 5):
        self.agent_id = agent_id
        self.state = AgentState.PENDING
        self.critique_count = 0
        self.max_iterations = max_iterations
        self._history: list[AgentState] = [AgentState.PENDING]

    def transition(self, new_state: AgentState) -> None:
        allowed = VALID_TRANSITIONS.get(self.state, [])
        if new_state not in allowed:
            raise ValueError(
                f"Invalid transition: {self.state} -> {new_state}. Allowed: {allowed}"
            )
        self.state = new_state
        self._history.append(new_state)

    def increment_critique(self) -> None:
        self.critique_count += 1

    def max_iterations_reached(self) -> bool:
        return self.critique_count >= self.max_iterations

    def history(self) -> list[AgentState]:
        return list(self._history)

    def next_critique_state(self) -> AgentState:
        mapping = {
            1: AgentState.DESIGN_CRITIQUE_1,
            2: AgentState.DESIGN_CRITIQUE_2,
            3: AgentState.DESIGN_CRITIQUE_3,
            4: AgentState.DESIGN_CRITIQUE_4,
            5: AgentState.DESIGN_CRITIQUE_5,
        }
        next_iter = self.critique_count + 1
        return mapping.get(next_iter, AgentState.DESIGN_CRITIQUE_5)
