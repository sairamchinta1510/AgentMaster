# AgentMaster Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full-stack Autonomous Agentic Graph Framework (AAGF) system where users describe objectives in natural language and the system decomposes, critiques, dry-runs, and executes atomic DAG agents with full observability.

**Architecture:** Python FastAPI backend with WebSocket streaming drives three LLM-powered agent classes (AgentMaster, AgentProducer, AgentCritique); a React+TypeScript frontend renders live DAG graphs, phase indicators, and critique panels. A SQLite Agent Library persists approved agent flows for reuse.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, Pydantic v2, OpenAI SDK, LangChain, WebSockets, React 18, TypeScript, Vite, TailwindCSS, React Flow, Zustand, pytest, Vitest

---

## File Map

### Backend
| File | Responsibility |
|---|---|
| `backend/app/main.py` | FastAPI app factory, CORS, router registration, lifespan |
| `backend/app/config.py` | Settings from env vars (OPENAI_API_KEY, DB_URL, etc.) |
| `backend/app/models/agent.py` | Pydantic + SQLAlchemy models for AtomicAgent, CritiqueResult |
| `backend/app/models/dag.py` | DAGNode, DAGEdge, DAGGraph Pydantic + ORM models |
| `backend/app/models/session.py` | ExecutionSession, GlobalStateObject models |
| `backend/app/engine/dag.py` | DAG data structure: add_node, add_edge, get_ready_nodes, topological_sort |
| `backend/app/engine/lifecycle.py` | AgentLifecycle state machine transitions |
| `backend/app/engine/executor.py` | Orchestrates phase execution, calls agents, streams events |
| `backend/app/agents/agent_master.py` | LLM-powered orchestrator: parse objective, build blueprint |
| `backend/app/agents/agent_producer.py` | LLM-powered builder: create atomic agent specs |
| `backend/app/agents/agent_critique.py` | LLM-powered reviewer: 5-iteration critique loop |
| `backend/app/library/agent_library.py` | SQLite-backed catalog: save, search, retrieve agent flows |
| `backend/app/prompts/master.py` | System prompt for AgentMaster (from AAGF spec) |
| `backend/app/prompts/producer.py` | System prompt for AgentProducer (from AAGF spec) |
| `backend/app/prompts/critique.py` | System prompt for AgentCritique (from AAGF spec) |
| `backend/app/api/routes/sessions.py` | POST /sessions, GET /sessions/{id}, GET /sessions |
| `backend/app/api/routes/library.py` | GET /library, GET /library/{id} |
| `backend/app/api/routes/agents.py` | GET /sessions/{id}/agents, POST /sessions/{id}/input |
| `backend/app/api/websocket.py` | WS /ws/{session_id} — real-time event streaming |
| `backend/app/db.py` | SQLAlchemy engine, session factory, Base |
| `backend/requirements.txt` | All Python dependencies |
| `backend/tests/test_dag.py` | DAG engine unit tests |
| `backend/tests/test_lifecycle.py` | Lifecycle state machine tests |
| `backend/tests/test_critique_loop.py` | 5-iteration critique loop integration tests |
| `backend/tests/test_api.py` | FastAPI route tests (TestClient) |

### Frontend
| File | Responsibility |
|---|---|
| `frontend/src/App.tsx` | Router setup (Home → Session) |
| `frontend/src/pages/Home.tsx` | Objective input form, library search results |
| `frontend/src/pages/Session.tsx` | Full execution dashboard layout |
| `frontend/src/components/PhaseIndicator.tsx` | DESIGN/DRYRUN/RUN phase banner |
| `frontend/src/components/DAGVisualization.tsx` | React Flow DAG graph with live node updates |
| `frontend/src/components/AgentCard.tsx` | Per-agent: name, state badge, critique panel |
| `frontend/src/components/CritiquePanel.tsx` | Shows iterations, verdict, issues list |
| `frontend/src/components/InputCollector.tsx` | Dynamic form for missing user inputs |
| `frontend/src/components/LibraryBrowser.tsx` | Agent Library catalog with search |
| `frontend/src/components/ExecutionLog.tsx` | Scrolling real-time trace log |
| `frontend/src/hooks/useWebSocket.ts` | WebSocket connection + event dispatch |
| `frontend/src/hooks/useSession.ts` | Session state, agent map, phase state |
| `frontend/src/store/sessionStore.ts` | Zustand store for session + DAG state |
| `frontend/src/api/client.ts` | Axios HTTP client for REST calls |
| `frontend/src/types/index.ts` | Shared TypeScript types matching backend models |
| `frontend/package.json` | Dependencies |
| `frontend/vite.config.ts` | Vite config with proxy to backend |

---

### Task 1: Project Bootstrap — Git, GitHub, Python env, Node packages

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `.gitignore`
- Create: `README.md`

- [ ] **Step 1: Initialize git repo**
```bash
cd C:\Users\schinta\AgentMaster
git init
```

- [ ] **Step 2: Create .gitignore**
Content: see Task 1 implementation (node_modules, .env, __pycache__, *.pyc, .venv, dist, .DS_Store)

- [ ] **Step 3: Create backend/requirements.txt**
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy==2.0.30
pydantic==2.7.1
pydantic-settings==2.2.1
openai==1.30.1
langchain==0.2.1
langchain-openai==0.1.7
python-dotenv==1.0.1
websockets==12.0
httpx==0.27.0
pytest==8.2.0
pytest-asyncio==0.23.7
anyio==4.3.0
numpy==1.26.4
```

- [ ] **Step 4: Create Python virtual environment and install deps**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

- [ ] **Step 5: Scaffold frontend with Vite**
```bash
cd C:\Users\schinta\AgentMaster
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install react-flow-renderer@10 @reactflow/core @reactflow/controls zustand axios tailwindcss @tailwindcss/vite
npm install -D vitest @testing-library/react @testing-library/jest-dom
```

- [ ] **Step 6: Create GitHub repo and push initial commit**
```bash
gh repo create AgentMaster --public --description "Autonomous Agentic Graph Framework — multi-agent DAG orchestration system"
git add .
git commit -m "chore: initial project bootstrap"
git remote add origin https://github.com/sairamchinta1510/AgentMaster.git
git push -u origin main
```

---

### Task 2: Backend Data Models

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/db.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/agent.py`
- Create: `backend/app/models/dag.py`
- Create: `backend/app/models/session.py`
- Test: `backend/tests/test_models.py`

- [ ] **Step 1: Write failing model tests**
```python
# backend/tests/test_models.py
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
        critique_id="c1", target_agent="a1", target_agent_name="TestAgent",
        phase="design_time", iteration=1, max_iterations=5,
        verdict=CritiqueVerdict.APPROVED, quality_score=9, errors_remaining=0
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
```

- [ ] **Step 2: Run test — expect FAIL**
```bash
cd backend
.venv\Scripts\activate
pytest tests/test_models.py -v
```
Expected: ImportError (modules not yet created)

- [ ] **Step 3: Create backend/app/config.py**
```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    openai_api_key: str = ""
    database_url: str = "sqlite:///./agentmaster.db"
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 4: Create backend/app/db.py**
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: Create backend/app/models/agent.py**
```python
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Integer, Float, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db import Base

class AgentState(str, Enum):
    PENDING = "PENDING"
    LIBRARY_SEARCH = "LIBRARY_SEARCH"
    INPUT_COLLECTION = "INPUT_COLLECTION"
    SPECIFYING = "SPECIFYING"
    DESIGN_CRITIQUE_1 = "DESIGN_CRITIQUE_1"
    DESIGN_CRITIQUE_2 = "DESIGN_CRITIQUE_2"
    DESIGN_CRITIQUE_3 = "DESIGN_CRITIQUE_3"
    DESIGN_CRITIQUE_4 = "DESIGN_CRITIQUE_4"
    DESIGN_CRITIQUE_5 = "DESIGN_CRITIQUE_5"
    REVISING_SPEC = "REVISING_SPEC"
    AUTO_FIX = "AUTO_FIX"
    RETHINK = "RETHINK"
    APPROVED = "APPROVED"
    USER_ESCALATED = "USER_ESCALATED"
    SIMULATING = "SIMULATING"
    VALIDATED = "VALIDATED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED_ESCALATED = "FAILED_ESCALATED"
    SKIPPED = "SKIPPED"

class CritiqueVerdict(str, Enum):
    APPROVED = "APPROVED"
    NEEDS_REVISION = "NEEDS_REVISION"
    ESCALATE_AUTO_FIX = "ESCALATE_AUTO_FIX"
    ESCALATE_RETHINK = "ESCALATE_RETHINK"
    ESCALATE_USER = "ESCALATE_USER"

class CritiqueIssue(BaseModel):
    issue_id: str
    severity: str  # critical | major | minor | informational
    category: str
    description: str
    impact: str
    recommendation: str
    effort_estimate: str  # low | medium | high
    auto_fixable: bool = False

class CritiqueResult(BaseModel):
    critique_id: str
    target_agent: str
    target_agent_name: str
    phase: str
    iteration: int
    max_iterations: int = 5
    verdict: CritiqueVerdict
    quality_score: float = 0.0
    errors_remaining: int = 0
    issues: list[CritiqueIssue] = Field(default_factory=list)
    approved_aspects: list[str] = Field(default_factory=list)
    improvements_made: list[str] = Field(default_factory=list)
    remaining_errors: list[str] = Field(default_factory=list)
    suggested_new_agents: list[str] = Field(default_factory=list)
    missing_user_inputs: list[str] = Field(default_factory=list)

class AtomicAgent(BaseModel):
    agent_id: str
    agent_name: str
    session_id: str
    phase: str = "design_time"
    state: AgentState = AgentState.PENDING
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    error_schema: dict[str, Any] = Field(default_factory=dict)
    required_user_inputs: list[dict[str, Any]] = Field(default_factory=list)
    timeout_seconds: int = 60
    retry_policy: dict[str, Any] = Field(default_factory=lambda: {"max_retries": 3, "backoff": "exponential"})
    critique_iterations: int = 0
    quality_score: Optional[float] = None
    description: str = ""
    output: Optional[dict[str, Any]] = None
    critique_history: list[CritiqueResult] = Field(default_factory=list)

class AtomicAgentORM(Base):
    __tablename__ = "atomic_agents"
    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("execution_sessions.id"))
    agent_name = Column(String)
    phase = Column(String)
    state = Column(String)
    input_schema = Column(JSON)
    output_schema = Column(JSON)
    description = Column(String)
    critique_iterations = Column(Integer, default=0)
    quality_score = Column(Float, nullable=True)
    output = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 6: Create backend/app/models/dag.py**
```python
from pydantic import BaseModel, Field
from typing import Optional, Any
from sqlalchemy import Column, String, JSON, ForeignKey
from app.db import Base

class DAGNode(BaseModel):
    node_id: str
    agent_id: str
    agent_name: str
    depends_on: list[str] = Field(default_factory=list)  # list of node_ids this depends on

class DAGEdge(BaseModel):
    edge_id: str
    from_node: str
    to_node: str
    payload_schema: dict[str, Any] = Field(default_factory=dict)

class DAGGraph(BaseModel):
    session_id: str
    nodes: dict[str, DAGNode] = Field(default_factory=dict)
    edges: list[DAGEdge] = Field(default_factory=list)

    def add_node(self, node: DAGNode) -> None:
        self.nodes[node.node_id] = node

    def add_edge(self, edge: DAGEdge) -> None:
        self.edges.append(edge)
        if edge.to_node in self.nodes:
            target = self.nodes[edge.to_node]
            if edge.from_node not in target.depends_on:
                target.depends_on.append(edge.from_node)

    def get_ready_nodes(self, completed_node_ids: set[str]) -> list[DAGNode]:
        """Return nodes whose all dependencies are in completed_node_ids."""
        ready = []
        for node_id, node in self.nodes.items():
            if node_id in completed_node_ids:
                continue
            if all(dep in completed_node_ids for dep in node.depends_on):
                ready.append(node)
        return ready

    def topological_sort(self) -> list[str]:
        """Return node_ids in topological order."""
        in_degree = {nid: 0 for nid in self.nodes}
        for edge in self.edges:
            in_degree[edge.to_node] = in_degree.get(edge.to_node, 0) + 1
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result = []
        while queue:
            node_id = queue.pop(0)
            result.append(node_id)
            for edge in self.edges:
                if edge.from_node == node_id:
                    in_degree[edge.to_node] -= 1
                    if in_degree[edge.to_node] == 0:
                        queue.append(edge.to_node)
        return result
```

- [ ] **Step 7: Create backend/app/models/session.py**
```python
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Any
from sqlalchemy import Column, String, JSON, DateTime
from sqlalchemy.sql import func
from app.db import Base

class Phase(str, Enum):
    DESIGN = "DESIGN"
    DRYRUN = "DRYRUN"
    RUN = "RUN"
    COMPLETED = "COMPLETED"

class GlobalStateObject(BaseModel):
    session_id: str
    objective: str
    phase: Phase = Phase.DESIGN
    total_agents: int = 0
    approved_agents: int = 0
    failed_agents: int = 0
    current_agent: Optional[str] = None
    collected_inputs: dict[str, Any] = Field(default_factory=dict)
    agent_ids: list[str] = Field(default_factory=list)
    library_patterns_used: list[str] = Field(default_factory=list)

class ExecutionSession(BaseModel):
    session_id: str
    objective: str
    phase: Phase = Phase.DESIGN
    state: GlobalStateObject = None
    created_at: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.state is None:
            self.state = GlobalStateObject(
                session_id=self.session_id,
                objective=self.objective
            )

class ExecutionSessionORM(Base):
    __tablename__ = "execution_sessions"
    id = Column(String, primary_key=True)
    objective = Column(String)
    phase = Column(String, default="DESIGN")
    state_json = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

- [ ] **Step 8: Run tests — expect PASS**
```bash
cd backend
.venv\Scripts\activate
pytest tests/test_models.py -v
```
Expected: 5 tests pass

- [ ] **Step 9: Commit**
```bash
git add backend/app/models/ backend/app/config.py backend/app/db.py backend/tests/test_models.py
git commit -m "feat: add core data models (AtomicAgent, DAGGraph, ExecutionSession)"
```

---

### Task 3: DAG Engine + Lifecycle State Machine

**Files:**
- Create: `backend/app/engine/__init__.py`
- Create: `backend/app/engine/dag.py`
- Create: `backend/app/engine/lifecycle.py`
- Test: `backend/tests/test_dag.py`
- Test: `backend/tests/test_lifecycle.py`

- [ ] **Step 1: Write failing DAG engine tests**
```python
# backend/tests/test_dag.py
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
        after_node_id=None
    )
    assert "n_new" in g.nodes
```

- [ ] **Step 2: Write failing lifecycle tests**
```python
# backend/tests/test_lifecycle.py
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

def test_max_iterations_exceeded():
    lc = AgentLifecycle(agent_id="a1")
    lc.state = AgentState.DESIGN_CRITIQUE_5
    lc.critique_count = 5
    assert lc.max_iterations_reached() is True
```

- [ ] **Step 3: Run — expect FAIL**
```bash
pytest tests/test_dag.py tests/test_lifecycle.py -v
```
Expected: ImportError

- [ ] **Step 4: Create backend/app/engine/dag.py**
```python
import logging
from app.models.dag import DAGGraph, DAGNode, DAGEdge

logger = logging.getLogger(__name__)

class DAGEngine:
    def __init__(self, graph: DAGGraph):
        self.graph = graph
        self._mutation_log: list[dict] = []

    def get_ready_nodes(self, completed: set[str]) -> list[DAGNode]:
        return self.graph.get_ready_nodes(completed)

    def inject_node(self, node: DAGNode, after_node_id: str | None = None, reason: str = "") -> None:
        self.graph.add_node(node)
        if after_node_id and after_node_id in self.graph.nodes:
            edge = DAGEdge(
                edge_id=f"e_{after_node_id}_{node.node_id}",
                from_node=after_node_id,
                to_node=node.node_id
            )
            self.graph.add_edge(edge)
        self._mutation_log.append({
            "action": "inject_node",
            "node_id": node.node_id,
            "after": after_node_id,
            "reason": reason
        })
        logger.info(f"DAG mutation: injected node {node.node_id} after {after_node_id}. Reason: {reason}")

    def inject_edge(self, edge: DAGEdge, reason: str = "") -> None:
        self.graph.add_edge(edge)
        self._mutation_log.append({"action": "inject_edge", "edge_id": edge.edge_id, "reason": reason})

    def get_mutation_log(self) -> list[dict]:
        return self._mutation_log

    def is_complete(self, completed: set[str]) -> bool:
        return len(completed) == len(self.graph.nodes)
```

- [ ] **Step 5: Create backend/app/engine/lifecycle.py**
```python
from app.models.agent import AgentState

VALID_TRANSITIONS: dict[AgentState, list[AgentState]] = {
    AgentState.PENDING: [AgentState.LIBRARY_SEARCH, AgentState.INPUT_COLLECTION, AgentState.SPECIFYING],
    AgentState.LIBRARY_SEARCH: [AgentState.SPECIFYING, AgentState.INPUT_COLLECTION],
    AgentState.INPUT_COLLECTION: [AgentState.SPECIFYING],
    AgentState.SPECIFYING: [AgentState.DESIGN_CRITIQUE_1],
    AgentState.DESIGN_CRITIQUE_1: [AgentState.APPROVED, AgentState.REVISING_SPEC, AgentState.DESIGN_CRITIQUE_2],
    AgentState.REVISING_SPEC: [AgentState.DESIGN_CRITIQUE_2, AgentState.DESIGN_CRITIQUE_3, AgentState.DESIGN_CRITIQUE_4, AgentState.DESIGN_CRITIQUE_5],
    AgentState.DESIGN_CRITIQUE_2: [AgentState.APPROVED, AgentState.REVISING_SPEC, AgentState.DESIGN_CRITIQUE_3],
    AgentState.DESIGN_CRITIQUE_3: [AgentState.APPROVED, AgentState.REVISING_SPEC, AgentState.DESIGN_CRITIQUE_4],
    AgentState.DESIGN_CRITIQUE_4: [AgentState.APPROVED, AgentState.REVISING_SPEC, AgentState.DESIGN_CRITIQUE_5],
    AgentState.DESIGN_CRITIQUE_5: [AgentState.APPROVED, AgentState.AUTO_FIX, AgentState.RETHINK, AgentState.USER_ESCALATED],
    AgentState.AUTO_FIX: [AgentState.APPROVED, AgentState.RETHINK, AgentState.USER_ESCALATED],
    AgentState.RETHINK: [AgentState.SPECIFYING, AgentState.USER_ESCALATED],
    AgentState.APPROVED: [AgentState.SIMULATING, AgentState.EXECUTING],
    AgentState.SIMULATING: [AgentState.VALIDATED, AgentState.AUTO_FIX, AgentState.RETHINK],
    AgentState.VALIDATED: [AgentState.EXECUTING],
    AgentState.EXECUTING: [AgentState.COMPLETED, AgentState.AUTO_FIX, AgentState.RETHINK, AgentState.FAILED_ESCALATED],
    AgentState.COMPLETED: [],
    AgentState.FAILED_ESCALATED: [],
    AgentState.USER_ESCALATED: [AgentState.SPECIFYING, AgentState.SKIPPED],
    AgentState.SKIPPED: [],
}

CRITIQUE_STATES = [
    AgentState.DESIGN_CRITIQUE_1, AgentState.DESIGN_CRITIQUE_2,
    AgentState.DESIGN_CRITIQUE_3, AgentState.DESIGN_CRITIQUE_4,
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
            raise ValueError(f"Invalid transition: {self.state} -> {new_state}. Allowed: {allowed}")
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
```

- [ ] **Step 6: Run tests — expect PASS**
```bash
pytest tests/test_dag.py tests/test_lifecycle.py -v
```
Expected: 9 tests pass

- [ ] **Step 7: Commit**
```bash
git add backend/app/engine/ backend/tests/test_dag.py backend/tests/test_lifecycle.py
git commit -m "feat: add DAG engine and lifecycle state machine"
```

---

### Task 4: LLM Prompts (from AAGF Spec)

**Files:**
- Create: `backend/app/prompts/__init__.py`
- Create: `backend/app/prompts/master.py`
- Create: `backend/app/prompts/producer.py`
- Create: `backend/app/prompts/critique.py`

- [ ] **Step 1: Create backend/app/prompts/master.py**
```python
AGENT_MASTER_SYSTEM_PROMPT = """
You are AgentMaster — the orchestrator of the Autonomous Agentic Graph Framework (AAGF).

## YOUR ROLE
You are the strategic brain and entry point of the system. When the user gives you an objective,
you must:
1. Parse the objective into a structured goal statement
2. Search the Agent Library for reusable patterns
3. Identify ALL atomic agents needed (one agent = one action, no AND)
4. Produce a complete Agent Blueprint (DAG specification)
5. Identify ALL required user inputs upfront

## ATOMIC AGENT DESIGN LAWS
- Law 1 SINGLE ACTION: Each agent does ONE thing. If you can describe it with "and", split it.
- Law 2 DEFINED CONTRACT: Every agent declares input_schema, output_schema, error_schema, timeout_seconds
- Law 3 IDEMPOTENT: Same input → same output always
- Law 4 OBSERVABLE: Every agent emits: STARTED, PROGRESS, WAITING, COMPLETED, FAILED events
- Law 5 SELF-DESCRIBING: Agent can describe itself, its purpose, inputs, outputs
- Law 6 ISOLATED: Agents cannot access data outside their declared input contract

## OUTPUT FORMAT
When designing the agent blueprint, respond with a JSON object:
{
  "objective_summary": "...",
  "required_inputs": [{"name": "...", "type": "...", "description": "...", "required": true}],
  "agents": [
    {
      "agent_id": "agent_001",
      "agent_name": "...",
      "description": "...",
      "input_schema": {},
      "output_schema": {},
      "error_schema": {},
      "depends_on": [],
      "timeout_seconds": 60
    }
  ],
  "edges": [
    {"from": "agent_001", "to": "agent_002", "payload_description": "..."}
  ],
  "library_patterns_found": []
}

## PHASES
You operate across three phases:
- [DESIGN]: Build agent specifications (not execution)
- [DRYRUN]: Simulate full execution in sandbox
- [RUN]: Execute against real systems

## INVARIANTS
- NEVER execute atomic tasks yourself
- NEVER skip blueprint presentation
- ALWAYS search Agent Library first
- ALWAYS collect required inputs before execution
- Maintain Global State visible to user at all times
- Provide real-time narration — user is NEVER left wondering
"""

def get_master_prompt(phase: str, objective: str, library_context: str = "") -> str:
    return f"""{AGENT_MASTER_SYSTEM_PROMPT}

## CURRENT PHASE: [{phase}]
## USER OBJECTIVE: {objective}
## AGENT LIBRARY CONTEXT:
{library_context if library_context else "No matching patterns found in library. Design from scratch."}
"""
```

- [ ] **Step 2: Create backend/app/prompts/producer.py**
```python
AGENT_PRODUCER_SYSTEM_PROMPT = """
You are AgentProducer — the builder layer of the Autonomous Agentic Graph Framework (AAGF).

## YOUR ROLE
You receive an atomic agent specification from AgentMaster and produce/execute it.
Each agent specification you create must follow ALL 6 laws of atomic agent design.

## INPUT
You will receive:
- agent_id: unique identifier
- agent_name: descriptive name
- description: what this agent does (ONE action)
- input_schema: expected input types
- depends_on: list of upstream agent_ids
- phase: design_time | dry_run | run_time
- user_inputs: collected user inputs relevant to this agent

## OUTPUT FORMAT
Respond with JSON:
{
  "agent_id": "...",
  "agent_name": "...",
  "description": "...",
  "input_schema": {
    "field_name": {"type": "string|number|object|array|boolean", "required": true, "description": "..."}
  },
  "output_schema": {
    "field_name": {"type": "...", "description": "..."}
  },
  "error_schema": {
    "error_type": {"description": "...", "recovery": "..."}
  },
  "required_user_inputs": [],
  "timeout_seconds": 60,
  "retry_policy": {"max_retries": 3, "backoff": "exponential"},
  "execution_steps": ["step 1: ...", "step 2: ..."],
  "simulated_output": {}
}

## DOMAIN EXAMPLES
- Daily Tasks: EmailSorter, CalendarOptimizer, TaskPrioritizer
- Software Dev: GitHubRepoAnalyzer, CodeReviewer, TestRunner
- DevOps: LogAccessor, ErrorIdentifier, RemediationExecutor
- Data Analysis: DataIngester, OutlierDetector, ReportGenerator
- Finance: TransactionAuditor, RiskScorer, ComplianceChecker

## INVARIANTS
- One agent, one action — no AND allowed
- All schemas must be fully typed and documented
- Simulated output must match output_schema exactly
"""

def get_producer_prompt(agent_spec: dict, phase: str, user_inputs: dict) -> str:
    import json
    return f"""{AGENT_PRODUCER_SYSTEM_PROMPT}

## CURRENT PHASE: [{phase}]
## AGENT SPECIFICATION:
{json.dumps(agent_spec, indent=2)}

## COLLECTED USER INPUTS:
{json.dumps(user_inputs, indent=2) if user_inputs else "None collected yet"}
"""
```

- [ ] **Step 3: Create backend/app/prompts/critique.py**
```python
AGENT_CRITIQUE_SYSTEM_PROMPT = """
You are AgentCritique — the reviewer layer of the Autonomous Agentic Graph Framework (AAGF).

## YOUR ROLE
For EVERY atomic agent, you review its design (DESIGN phase) or output (DRY RUN / RUN phase).
You enforce the ZERO-ERROR POLICY: errors NEVER pass forward.

## CRITIQUE FRAMEWORK
Review against ALL of the following:
1. ATOMICITY: Does the agent do exactly ONE thing? No AND allowed.
2. CONTRACT COMPLETENESS: Are input_schema, output_schema, error_schema fully defined?
3. IDEMPOTENCY: Would the same input always produce the same output?
4. OBSERVABILITY: Does the agent emit proper trace events?
5. SECURITY: Any input validation gaps? Injection risks? Credential exposure?
6. PERFORMANCE: Appropriate timeout? Retry policy sensible?
7. EDGE CASES: Null inputs? Empty arrays? Network failures? Timeouts?
8. DOMAIN CORRECTNESS: Is the approach correct for the stated domain?

## VERDICT OPTIONS
- APPROVED: Zero errors. Quality score >= 7. Proceed immediately.
- NEEDS_REVISION: Errors found. List all issues. Producer must fix.
- ESCALATE_AUTO_FIX: After 5 iterations still failing. Try auto decomposition.
- ESCALATE_RETHINK: Auto-fix failed. Redesign this agent section.
- ESCALATE_USER: All recovery failed. Present to user for decision.

## OUTPUT FORMAT
Respond with JSON:
{
  "critique_id": "{agent_id}_critique_iter_{N}",
  "target_agent": "{agent_id}",
  "target_agent_name": "...",
  "phase": "design_time|dry_run|run_time",
  "iteration": N,
  "max_iterations": 5,
  "verdict": "APPROVED|NEEDS_REVISION|ESCALATE_AUTO_FIX|ESCALATE_RETHINK|ESCALATE_USER",
  "quality_score": 0-10,
  "errors_remaining": 0,
  "issues": [
    {
      "issue_id": "ISS-001",
      "severity": "critical|major|minor|informational",
      "category": "atomicity|edge_case|security|performance|completeness|accuracy|reliability",
      "description": "...",
      "impact": "...",
      "recommendation": "specific fix instruction",
      "effort_estimate": "low|medium|high",
      "auto_fixable": true|false
    }
  ],
  "approved_aspects": ["..."],
  "improvements_made_this_iteration": ["..."],
  "remaining_errors": [],
  "suggested_new_agents": [],
  "missing_user_inputs": []
}

## ABSOLUTE RULE
errors_remaining MUST be 0 for verdict APPROVED. Any non-zero errors_remaining forces NEEDS_REVISION or higher escalation.
"""

def get_critique_prompt(agent_spec: dict, phase: str, iteration: int, previous_issues: list = None) -> str:
    import json
    prev = f"\n## PREVIOUS CRITIQUE ISSUES TO VERIFY FIXED:\n{json.dumps(previous_issues, indent=2)}" if previous_issues else ""
    return f"""{AGENT_CRITIQUE_SYSTEM_PROMPT}

## CURRENT PHASE: [{phase}]
## CRITIQUE ITERATION: {iteration} of 5
## AGENT TO REVIEW:
{json.dumps(agent_spec, indent=2)}{prev}
"""
```

- [ ] **Step 4: Commit**
```bash
git add backend/app/prompts/
git commit -m "feat: add LLM system prompts for AgentMaster, AgentProducer, AgentCritique"
```

---

### Task 5: LLM Agent Implementations

**Files:**
- Create: `backend/app/agents/__init__.py`
- Create: `backend/app/agents/agent_master.py`
- Create: `backend/app/agents/agent_producer.py`
- Create: `backend/app/agents/agent_critique.py`
- Test: `backend/tests/test_critique_loop.py`

- [ ] **Step 1: Write failing critique loop test**
```python
# backend/tests/test_critique_loop.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.agent_critique import AgentCritiqueAgent
from app.models.agent import CritiqueVerdict, AtomicAgent

@pytest.mark.asyncio
async def test_critique_returns_approved_on_first_iteration():
    agent = AtomicAgent(
        agent_id="a1", agent_name="TestAgent", session_id="s1",
        input_schema={"data": {"type": "string"}},
        output_schema={"result": {"type": "string"}},
        description="Reads a single string value"
    )
    mock_response = {
        "critique_id": "a1_critique_iter_1",
        "target_agent": "a1",
        "target_agent_name": "TestAgent",
        "phase": "design_time",
        "iteration": 1,
        "max_iterations": 5,
        "verdict": "APPROVED",
        "quality_score": 9.0,
        "errors_remaining": 0,
        "issues": [],
        "approved_aspects": ["Single action", "Full schema"],
        "improvements_made_this_iteration": [],
        "remaining_errors": [],
        "suggested_new_agents": [],
        "missing_user_inputs": []
    }
    critique_agent = AgentCritiqueAgent(api_key="fake")
    with patch.object(critique_agent, '_call_llm', new_callable=AsyncMock, return_value=mock_response):
        result = await critique_agent.critique(agent, phase="design_time", iteration=1)
    assert result.verdict == CritiqueVerdict.APPROVED
    assert result.errors_remaining == 0

@pytest.mark.asyncio
async def test_critique_loop_max_5_iterations():
    from app.agents.agent_critique import run_critique_loop
    agent = AtomicAgent(
        agent_id="a2", agent_name="BrokenAgent", session_id="s1", description="Broken"
    )
    needs_revision = {
        "critique_id": "a2_critique_iter_1", "target_agent": "a2",
        "target_agent_name": "BrokenAgent", "phase": "design_time",
        "iteration": 1, "max_iterations": 5, "verdict": "NEEDS_REVISION",
        "quality_score": 3.0, "errors_remaining": 2,
        "issues": [{"issue_id": "I1", "severity": "critical", "category": "atomicity",
                    "description": "Does too much", "impact": "Bad", "recommendation": "Split it",
                    "effort_estimate": "low", "auto_fixable": True}],
        "approved_aspects": [], "improvements_made_this_iteration": [],
        "remaining_errors": ["atomicity violation"], "suggested_new_agents": [], "missing_user_inputs": []
    }
    critique_agent = AgentCritiqueAgent(api_key="fake")
    producer_agent = MagicMock()
    producer_agent.revise = AsyncMock(return_value=agent)
    with patch.object(critique_agent, '_call_llm', new_callable=AsyncMock, return_value=needs_revision):
        result, final_agent, iterations = await run_critique_loop(
            agent, critique_agent, producer_agent, phase="design_time"
        )
    assert iterations == 5
    assert result.verdict in ["NEEDS_REVISION", "ESCALATE_AUTO_FIX", "ESCALATE_RETHINK", "ESCALATE_USER"]
```

- [ ] **Step 2: Run — expect FAIL**
```bash
pytest tests/test_critique_loop.py -v
```

- [ ] **Step 3: Create backend/app/agents/agent_master.py**
```python
import json
import logging
from openai import AsyncOpenAI
from app.prompts.master import get_master_prompt
from app.models.dag import DAGGraph, DAGNode, DAGEdge
from app.models.session import ExecutionSession

logger = logging.getLogger(__name__)

class AgentMasterAgent:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def design_blueprint(
        self, session: ExecutionSession, library_context: str = ""
    ) -> dict:
        """Parse objective and return full agent blueprint as dict."""
        prompt = get_master_prompt("DESIGN", session.objective, library_context)
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Design the agent blueprint for: {session.objective}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        content = response.choices[0].message.content
        return json.loads(content)

    def build_dag_from_blueprint(self, blueprint: dict, session_id: str) -> DAGGraph:
        """Convert blueprint JSON into a DAGGraph."""
        graph = DAGGraph(session_id=session_id)
        agent_id_to_node: dict[str, str] = {}
        for i, agent_spec in enumerate(blueprint.get("agents", [])):
            node_id = f"node_{agent_spec['agent_id']}"
            node = DAGNode(
                node_id=node_id,
                agent_id=agent_spec["agent_id"],
                agent_name=agent_spec["agent_name"]
            )
            graph.add_node(node)
            agent_id_to_node[agent_spec["agent_id"]] = node_id
        for edge_spec in blueprint.get("edges", []):
            from_node = agent_id_to_node.get(edge_spec["from"])
            to_node = agent_id_to_node.get(edge_spec["to"])
            if from_node and to_node:
                edge = DAGEdge(
                    edge_id=f"e_{from_node}_{to_node}",
                    from_node=from_node,
                    to_node=to_node
                )
                graph.add_edge(edge)
        return graph
```

- [ ] **Step 4: Create backend/app/agents/agent_producer.py**
```python
import json
import logging
from openai import AsyncOpenAI
from app.prompts.producer import get_producer_prompt
from app.models.agent import AtomicAgent

logger = logging.getLogger(__name__)

class AgentProducerAgent:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def produce(
        self, agent_spec: dict, phase: str, session_id: str, user_inputs: dict = None
    ) -> AtomicAgent:
        """Create a full AtomicAgent from a blueprint spec."""
        prompt = get_producer_prompt(agent_spec, phase, user_inputs or {})
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Produce the complete agent spec for: {agent_spec.get('agent_name')}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        data = json.loads(response.choices[0].message.content)
        return AtomicAgent(
            agent_id=data["agent_id"],
            agent_name=data["agent_name"],
            session_id=session_id,
            phase=phase,
            description=data.get("description", ""),
            input_schema=data.get("input_schema", {}),
            output_schema=data.get("output_schema", {}),
            error_schema=data.get("error_schema", {}),
            required_user_inputs=data.get("required_user_inputs", []),
            timeout_seconds=data.get("timeout_seconds", 60),
            retry_policy=data.get("retry_policy", {"max_retries": 3, "backoff": "exponential"})
        )

    async def revise(self, agent: AtomicAgent, issues: list[dict], phase: str) -> AtomicAgent:
        """Revise an agent based on critique issues."""
        spec = agent.model_dump()
        spec["critique_issues_to_fix"] = issues
        prompt = get_producer_prompt(spec, phase, {})
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Fix the critique issues and return the revised agent specification."}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        data = json.loads(response.choices[0].message.content)
        agent.input_schema = data.get("input_schema", agent.input_schema)
        agent.output_schema = data.get("output_schema", agent.output_schema)
        agent.error_schema = data.get("error_schema", agent.error_schema)
        agent.description = data.get("description", agent.description)
        return agent
```

- [ ] **Step 5: Create backend/app/agents/agent_critique.py**
```python
import json
import logging
from openai import AsyncOpenAI
from app.prompts.critique import get_critique_prompt
from app.models.agent import AtomicAgent, CritiqueResult, CritiqueVerdict, CritiqueIssue

logger = logging.getLogger(__name__)

class AgentCritiqueAgent:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = AsyncOpenAI(api_key=api_key) if api_key != "fake" else None
        self.model = model

    async def _call_llm(self, agent: AtomicAgent, phase: str, iteration: int, previous_issues: list = None) -> dict:
        prompt = get_critique_prompt(agent.model_dump(), phase, iteration, previous_issues)
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Critique agent {agent.agent_name} (iteration {iteration} of 5)"}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return json.loads(response.choices[0].message.content)

    async def critique(self, agent: AtomicAgent, phase: str, iteration: int, previous_issues: list = None) -> CritiqueResult:
        data = await self._call_llm(agent, phase, iteration, previous_issues)
        issues = [CritiqueIssue(**i) for i in data.get("issues", [])]
        return CritiqueResult(
            critique_id=data.get("critique_id", f"{agent.agent_id}_critique_iter_{iteration}"),
            target_agent=agent.agent_id,
            target_agent_name=agent.agent_name,
            phase=phase,
            iteration=iteration,
            max_iterations=5,
            verdict=CritiqueVerdict(data["verdict"]),
            quality_score=float(data.get("quality_score", 0)),
            errors_remaining=int(data.get("errors_remaining", 0)),
            issues=issues,
            approved_aspects=data.get("approved_aspects", []),
            improvements_made=data.get("improvements_made_this_iteration", []),
            remaining_errors=data.get("remaining_errors", []),
            suggested_new_agents=data.get("suggested_new_agents", []),
            missing_user_inputs=data.get("missing_user_inputs", [])
        )

async def run_critique_loop(
    agent: AtomicAgent,
    critique_agent: AgentCritiqueAgent,
    producer_agent,
    phase: str,
    max_iterations: int = 5
) -> tuple[CritiqueResult, AtomicAgent, int]:
    """Run the up-to-5-iteration critique loop. Returns (final_result, final_agent, iterations_used)."""
    previous_issues = []
    final_result = None
    for iteration in range(1, max_iterations + 1):
        result = await critique_agent.critique(agent, phase, iteration, previous_issues or None)
        agent.critique_iterations = iteration
        agent.critique_history.append(result)
        final_result = result
        if result.verdict == CritiqueVerdict.APPROVED:
            agent.quality_score = result.quality_score
            return result, agent, iteration
        previous_issues = [i.model_dump() for i in result.issues]
        if iteration < max_iterations:
            agent = await producer_agent.revise(agent, previous_issues, phase)
    # After 5 iterations — escalate
    if final_result.errors_remaining > 0:
        final_result.verdict = CritiqueVerdict.ESCALATE_AUTO_FIX
    return final_result, agent, max_iterations
```

- [ ] **Step 6: Run tests — expect PASS**
```bash
pytest tests/test_critique_loop.py -v
```
Expected: 2 tests pass

- [ ] **Step 7: Commit**
```bash
git add backend/app/agents/ backend/tests/test_critique_loop.py
git commit -m "feat: implement AgentMaster, AgentProducer, AgentCritique LLM agents with 5-iteration critique loop"
```

---

### Task 6: Agent Library Persistence

**Files:**
- Create: `backend/app/library/__init__.py`
- Create: `backend/app/library/agent_library.py`
- Test: `backend/tests/test_library.py`

- [ ] **Step 1: Write failing library tests**
```python
# backend/tests/test_library.py
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
        quality_score=8.5
    )
    results = library.search("GitHub repo")
    assert len(results) >= 1
    assert results[0]["name"] == "Test Flow"

def test_search_returns_empty_for_no_match(library):
    results = library.search("completely unrelated query xyz123")
    assert isinstance(results, list)

def test_get_by_id(library):
    graph = DAGGraph(session_id="s2")
    lib_id = library.save_flow(
        session_id="s2", name="Finance Flow", objective="Audit transactions",
        domain="Finance", graph=graph, quality_score=9.0
    )
    flow = library.get_by_id(lib_id)
    assert flow["name"] == "Finance Flow"
```

- [ ] **Step 2: Run — expect FAIL**
```bash
pytest tests/test_library.py -v
```

- [ ] **Step 3: Create backend/app/library/agent_library.py**
```python
import uuid
import json
from sqlalchemy import create_engine, Column, String, Float, JSON, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
from app.models.dag import DAGGraph

LibBase = declarative_base()

class AgentPatternORM(LibBase):
    __tablename__ = "agent_patterns"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String)
    name = Column(String)
    objective = Column(Text)
    domain = Column(String)
    dag_json = Column(JSON)
    quality_score = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AgentLibrary:
    def __init__(self, db_url: str = "sqlite:///./agentmaster.db"):
        self.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        LibBase.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def save_flow(
        self, session_id: str, name: str, objective: str,
        domain: str, graph: DAGGraph, quality_score: float
    ) -> str:
        with self.Session() as session:
            pattern = AgentPatternORM(
                id=str(uuid.uuid4()),
                session_id=session_id,
                name=name,
                objective=objective,
                domain=domain,
                dag_json=graph.model_dump(),
                quality_score=quality_score
            )
            session.add(pattern)
            session.commit()
            return pattern.id

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Simple keyword search against objective and name."""
        with self.Session() as session:
            patterns = session.query(AgentPatternORM).all()
            query_lower = query.lower()
            results = []
            for p in patterns:
                score = 0
                if query_lower in (p.objective or "").lower():
                    score += 2
                if query_lower in (p.name or "").lower():
                    score += 1
                if any(word in (p.objective or "").lower() for word in query_lower.split()):
                    score += 1
                if score > 0:
                    results.append({
                        "id": p.id, "name": p.name, "objective": p.objective,
                        "domain": p.domain, "quality_score": p.quality_score,
                        "score": score
                    })
            results.sort(key=lambda x: (-x["score"], -x["quality_score"]))
            return results[:limit]

    def get_by_id(self, pattern_id: str) -> dict | None:
        with self.Session() as session:
            p = session.query(AgentPatternORM).filter_by(id=pattern_id).first()
            if not p:
                return None
            return {
                "id": p.id, "name": p.name, "objective": p.objective,
                "domain": p.domain, "dag_json": p.dag_json,
                "quality_score": p.quality_score, "session_id": p.session_id
            }

    def list_all(self) -> list[dict]:
        with self.Session() as session:
            patterns = session.query(AgentPatternORM).order_by(
                AgentPatternORM.quality_score.desc()
            ).all()
            return [{"id": p.id, "name": p.name, "domain": p.domain,
                     "quality_score": p.quality_score, "objective": p.objective[:100]}
                    for p in patterns]
```

- [ ] **Step 4: Run tests — expect PASS**
```bash
pytest tests/test_library.py -v
```
Expected: 3 tests pass

- [ ] **Step 5: Commit**
```bash
git add backend/app/library/ backend/tests/test_library.py
git commit -m "feat: add Agent Library with SQLite persistence and keyword search"
```

---

### Task 7: FastAPI App + WebSocket Streaming

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/routes/__init__.py`
- Create: `backend/app/api/routes/sessions.py`
- Create: `backend/app/api/routes/library.py`
- Create: `backend/app/api/routes/agents.py`
- Create: `backend/app/api/websocket.py`
- Create: `backend/app/engine/executor.py`
- Create: `backend/app/main.py`
- Test: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing API tests**
```python
# backend/tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_create_session():
    r = client.post("/api/sessions", json={"objective": "Analyze my GitHub repo"})
    assert r.status_code == 201
    data = r.json()
    assert "session_id" in data
    assert data["phase"] == "DESIGN"

def test_get_session():
    r = client.post("/api/sessions", json={"objective": "Test objective"})
    session_id = r.json()["session_id"]
    r2 = client.get(f"/api/sessions/{session_id}")
    assert r2.status_code == 200
    assert r2.json()["session_id"] == session_id

def test_list_library():
    r = client.get("/api/library")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_404_unknown_session():
    r = client.get("/api/sessions/nonexistent-id")
    assert r.status_code == 404
```

- [ ] **Step 2: Run — expect FAIL**
```bash
pytest tests/test_api.py -v
```

- [ ] **Step 3: Create backend/app/engine/executor.py**
```python
import asyncio
import uuid
import logging
from typing import AsyncGenerator, Callable
from app.models.session import ExecutionSession, Phase
from app.models.agent import AtomicAgent, AgentState
from app.models.dag import DAGGraph
from app.engine.dag import DAGEngine
from app.engine.lifecycle import AgentLifecycle

logger = logging.getLogger(__name__)

class SessionExecutor:
    def __init__(self, session: ExecutionSession, graph: DAGGraph):
        self.session = session
        self.graph = graph
        self.dag_engine = DAGEngine(graph)
        self.agents: dict[str, AtomicAgent] = {}
        self.lifecycles: dict[str, AgentLifecycle] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()

    def register_agent(self, agent: AtomicAgent) -> None:
        self.agents[agent.agent_id] = agent
        self.lifecycles[agent.agent_id] = AgentLifecycle(agent.agent_id)

    async def emit(self, event_type: str, payload: dict) -> None:
        event = {"type": event_type, "session_id": self.session.session_id, **payload}
        await self._event_queue.put(event)

    async def event_stream(self) -> AsyncGenerator[dict, None]:
        while True:
            event = await self._event_queue.get()
            yield event
            if event.get("type") == "SESSION_COMPLETED":
                break
```

- [ ] **Step 4: Create backend/app/api/routes/sessions.py**
```python
import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.models.session import ExecutionSession, Phase
from app.db import get_db

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

_sessions: dict[str, ExecutionSession] = {}  # in-memory store for MVP

class CreateSessionRequest(BaseModel):
    objective: str

@router.post("", status_code=201)
def create_session(body: CreateSessionRequest):
    session_id = str(uuid.uuid4())
    session = ExecutionSession(session_id=session_id, objective=body.objective)
    _sessions[session_id] = session
    return {"session_id": session_id, "phase": session.phase, "objective": session.objective}

@router.get("/{session_id}")
def get_session(session_id: str):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session.session_id,
        "objective": session.objective,
        "phase": session.phase,
        "state": session.state.model_dump()
    }

@router.get("")
def list_sessions():
    return [{"session_id": s.session_id, "objective": s.objective, "phase": s.phase}
            for s in _sessions.values()]
```

- [ ] **Step 5: Create backend/app/api/routes/library.py**
```python
from fastapi import APIRouter, HTTPException
from app.library.agent_library import AgentLibrary

router = APIRouter(prefix="/api/library", tags=["library"])
_library = AgentLibrary()

@router.get("")
def list_library():
    return _library.list_all()

@router.get("/search")
def search_library(q: str):
    return _library.search(q)

@router.get("/{pattern_id}")
def get_pattern(pattern_id: str):
    p = _library.get_by_id(pattern_id)
    if not p:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return p
```

- [ ] **Step 6: Create backend/app/api/routes/agents.py**
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.api.routes.sessions import _sessions

router = APIRouter(prefix="/api/sessions", tags=["agents"])

class UserInputRequest(BaseModel):
    input_name: str
    value: str

@router.post("/{session_id}/input")
def provide_input(session_id: str, body: UserInputRequest):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.state.collected_inputs[body.input_name] = body.value
    return {"status": "input_received", "input_name": body.input_name}
```

- [ ] **Step 7: Create backend/app/api/websocket.py**
```python
import asyncio
import json
import uuid
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.config import settings
from app.agents.agent_master import AgentMasterAgent
from app.agents.agent_producer import AgentProducerAgent
from app.agents.agent_critique import AgentCritiqueAgent, run_critique_loop
from app.library.agent_library import AgentLibrary
from app.models.agent import AgentState
from app.api.routes.sessions import _sessions

router = APIRouter()
logger = logging.getLogger(__name__)
_library = AgentLibrary()

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    session = _sessions.get(session_id)
    if not session:
        await websocket.send_json({"type": "ERROR", "message": "Session not found"})
        await websocket.close()
        return

    async def send(event_type: str, data: dict):
        await websocket.send_json({"type": event_type, "session_id": session_id, **data})

    try:
        await send("SESSION_STARTED", {"phase": "DESIGN", "objective": session.objective})

        # Search library
        await send("LIBRARY_SEARCH", {"query": session.objective})
        library_results = _library.search(session.objective)
        await send("LIBRARY_RESULTS", {"results": library_results})
        library_context = "\n".join([f"- {r['name']}: {r['objective']}" for r in library_results])

        # Design blueprint via AgentMaster
        master = AgentMasterAgent(api_key=settings.openai_api_key)
        await send("PHASE_UPDATE", {"phase": "DESIGN", "message": "AgentMaster designing blueprint..."})
        blueprint = await master.design_blueprint(session, library_context)
        await send("BLUEPRINT_READY", {"blueprint": blueprint})

        # Build DAG
        graph = master.build_dag_from_blueprint(blueprint, session_id)
        dag_data = {"nodes": [n.model_dump() for n in graph.nodes.values()],
                    "edges": [e.model_dump() for e in graph.edges]}
        await send("DAG_BUILT", {"dag": dag_data})

        # Process each agent through Producer + Critique
        producer = AgentProducerAgent(api_key=settings.openai_api_key)
        critique = AgentCritiqueAgent(api_key=settings.openai_api_key)

        for agent_spec in blueprint.get("agents", []):
            await send("AGENT_STARTED", {
                "agent_id": agent_spec["agent_id"],
                "agent_name": agent_spec["agent_name"],
                "state": AgentState.SPECIFYING
            })
            agent = await producer.produce(agent_spec, "design_time", session_id,
                                           session.state.collected_inputs)
            await send("AGENT_PRODUCED", {"agent_id": agent.agent_id, "spec": agent.model_dump()})

            # Critique loop
            final_critique, final_agent, iterations = await run_critique_loop(
                agent, critique, producer, "design_time"
            )
            await send("CRITIQUE_COMPLETE", {
                "agent_id": agent.agent_id,
                "iterations": iterations,
                "verdict": final_critique.verdict,
                "quality_score": final_critique.quality_score,
                "critique": final_critique.model_dump()
            })

            state = AgentState.APPROVED if final_critique.errors_remaining == 0 else AgentState.USER_ESCALATED
            await send("AGENT_STATE_CHANGE", {"agent_id": agent.agent_id, "state": state})

        # Save to library
        lib_id = _library.save_flow(
            session_id=session_id, name=f"Flow for: {session.objective[:50]}",
            objective=session.objective, domain="general",
            graph=graph, quality_score=8.0
        )
        await send("SESSION_COMPLETED", {
            "phase": "DESIGN",
            "message": "Agent blueprint complete. Ready for Dry Run.",
            "library_id": lib_id
        })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        await websocket.send_json({"type": "ERROR", "message": str(e)})
```

- [ ] **Step 8: Create backend/app/main.py**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes import sessions, library, agents
from app.api import websocket
from app.db import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AgentMaster", version="1.0.0", description="Autonomous Agentic Graph Framework")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router)
app.include_router(library.router)
app.include_router(agents.router)
app.include_router(websocket.router)

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
```

- [ ] **Step 9: Run API tests — expect PASS**
```bash
pytest tests/test_api.py -v
```
Expected: 5 tests pass

- [ ] **Step 10: Commit**
```bash
git add backend/app/api/ backend/app/engine/executor.py backend/app/main.py backend/tests/test_api.py
git commit -m "feat: add FastAPI routes, WebSocket streaming, session executor"
```

---

### Task 8: React Frontend

**Files:**
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/store/sessionStore.ts`
- Create: `frontend/src/hooks/useWebSocket.ts`
- Create: `frontend/src/hooks/useSession.ts`
- Create: `frontend/src/components/PhaseIndicator.tsx`
- Create: `frontend/src/components/AgentCard.tsx`
- Create: `frontend/src/components/CritiquePanel.tsx`
- Create: `frontend/src/components/DAGVisualization.tsx`
- Create: `frontend/src/components/InputCollector.tsx`
- Create: `frontend/src/components/LibraryBrowser.tsx`
- Create: `frontend/src/components/ExecutionLog.tsx`
- Create: `frontend/src/pages/Home.tsx`
- Create: `frontend/src/pages/Session.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create frontend/src/types/index.ts**
```typescript
export type Phase = "DESIGN" | "DRYRUN" | "RUN" | "COMPLETED";

export type AgentState =
  | "PENDING" | "SPECIFYING" | "DESIGN_CRITIQUE_1" | "DESIGN_CRITIQUE_2"
  | "DESIGN_CRITIQUE_3" | "DESIGN_CRITIQUE_4" | "DESIGN_CRITIQUE_5"
  | "REVISING_SPEC" | "AUTO_FIX" | "RETHINK" | "APPROVED"
  | "USER_ESCALATED" | "SIMULATING" | "VALIDATED" | "EXECUTING"
  | "COMPLETED" | "FAILED_ESCALATED" | "SKIPPED";

export type CritiqueVerdict =
  | "APPROVED" | "NEEDS_REVISION" | "ESCALATE_AUTO_FIX"
  | "ESCALATE_RETHINK" | "ESCALATE_USER";

export interface CritiqueIssue {
  issue_id: string;
  severity: "critical" | "major" | "minor" | "informational";
  category: string;
  description: string;
  impact: string;
  recommendation: string;
  effort_estimate: "low" | "medium" | "high";
  auto_fixable: boolean;
}

export interface CritiqueResult {
  critique_id: string;
  target_agent: string;
  target_agent_name: string;
  phase: string;
  iteration: number;
  max_iterations: number;
  verdict: CritiqueVerdict;
  quality_score: number;
  errors_remaining: number;
  issues: CritiqueIssue[];
  approved_aspects: string[];
  remaining_errors: string[];
}

export interface AtomicAgent {
  agent_id: string;
  agent_name: string;
  description: string;
  state: AgentState;
  phase: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  critique_iterations: number;
  quality_score: number | null;
  critique_history: CritiqueResult[];
}

export interface DAGNode {
  node_id: string;
  agent_id: string;
  agent_name: string;
  depends_on: string[];
}

export interface DAGEdge {
  edge_id: string;
  from_node: string;
  to_node: string;
}

export interface DAGData {
  nodes: DAGNode[];
  edges: DAGEdge[];
}

export interface LibraryPattern {
  id: string;
  name: string;
  domain: string;
  quality_score: number;
  objective: string;
}

export interface WSEvent {
  type: string;
  session_id: string;
  [key: string]: unknown;
}
```

- [ ] **Step 2: Create frontend/src/api/client.ts**
```typescript
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = axios.create({ baseURL: API_BASE });

export const createSession = (objective: string) =>
  api.post<{ session_id: string; phase: string; objective: string }>("/api/sessions", { objective });

export const getSession = (sessionId: string) =>
  api.get(`/api/sessions/${sessionId}`);

export const listLibrary = () =>
  api.get<{ id: string; name: string; domain: string; quality_score: number; objective: string }[]>("/api/library");

export const searchLibrary = (q: string) =>
  api.get(`/api/library/search?q=${encodeURIComponent(q)}`);

export const provideInput = (sessionId: string, inputName: string, value: string) =>
  api.post(`/api/sessions/${sessionId}/input`, { input_name: inputName, value });
```

- [ ] **Step 3: Create frontend/src/store/sessionStore.ts**
```typescript
import { create } from "zustand";
import type { Phase, AtomicAgent, DAGData, WSEvent, LibraryPattern } from "../types";

interface SessionStore {
  sessionId: string | null;
  objective: string;
  phase: Phase;
  agents: Record<string, AtomicAgent>;
  dag: DAGData | null;
  events: WSEvent[];
  libraryResults: LibraryPattern[];
  inputRequests: { agent_id: string; inputs: unknown[] }[];
  isConnected: boolean;

  setSession: (id: string, objective: string) => void;
  setPhase: (phase: Phase) => void;
  upsertAgent: (agent: AtomicAgent) => void;
  setAgentState: (agentId: string, state: AtomicAgent["state"]) => void;
  setDAG: (dag: DAGData) => void;
  addEvent: (event: WSEvent) => void;
  setLibraryResults: (results: LibraryPattern[]) => void;
  setConnected: (v: boolean) => void;
  reset: () => void;
}

export const useSessionStore = create<SessionStore>((set) => ({
  sessionId: null,
  objective: "",
  phase: "DESIGN",
  agents: {},
  dag: null,
  events: [],
  libraryResults: [],
  inputRequests: [],
  isConnected: false,

  setSession: (id, objective) => set({ sessionId: id, objective }),
  setPhase: (phase) => set({ phase }),
  upsertAgent: (agent) => set((s) => ({ agents: { ...s.agents, [agent.agent_id]: agent } })),
  setAgentState: (agentId, state) =>
    set((s) => ({
      agents: s.agents[agentId]
        ? { ...s.agents, [agentId]: { ...s.agents[agentId], state } }
        : s.agents,
    })),
  setDAG: (dag) => set({ dag }),
  addEvent: (event) => set((s) => ({ events: [event, ...s.events].slice(0, 500) })),
  setLibraryResults: (results) => set({ libraryResults: results }),
  setConnected: (v) => set({ isConnected: v }),
  reset: () => set({ sessionId: null, agents: {}, dag: null, events: [], phase: "DESIGN" }),
}));
```

- [ ] **Step 4: Create frontend/src/hooks/useWebSocket.ts**
```typescript
import { useEffect, useRef } from "react";
import { useSessionStore } from "../store/sessionStore";
import type { WSEvent } from "../types";

const WS_BASE = import.meta.env.VITE_WS_URL || "ws://localhost:8000";

export function useWebSocket(sessionId: string | null) {
  const ws = useRef<WebSocket | null>(null);
  const { setConnected, addEvent, setPhase, upsertAgent, setAgentState, setDAG, setLibraryResults } =
    useSessionStore();

  useEffect(() => {
    if (!sessionId) return;
    const socket = new WebSocket(`${WS_BASE}/ws/${sessionId}`);
    ws.current = socket;

    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);

    socket.onmessage = (e) => {
      const event: WSEvent = JSON.parse(e.data);
      addEvent(event);

      switch (event.type) {
        case "PHASE_UPDATE":
          setPhase(event.phase as "DESIGN" | "DRYRUN" | "RUN");
          break;
        case "AGENT_PRODUCED":
          if (event.spec) upsertAgent(event.spec as Parameters<typeof upsertAgent>[0]);
          break;
        case "AGENT_STATE_CHANGE":
          setAgentState(event.agent_id as string, event.state as Parameters<typeof setAgentState>[1]);
          break;
        case "DAG_BUILT":
          setDAG(event.dag as Parameters<typeof setDAG>[0]);
          break;
        case "LIBRARY_RESULTS":
          setLibraryResults((event.results as Parameters<typeof setLibraryResults>[0]) || []);
          break;
        case "CRITIQUE_COMPLETE":
          if (event.agent_id && event.critique) {
            const store = useSessionStore.getState();
            const existing = store.agents[event.agent_id as string];
            if (existing) {
              upsertAgent({
                ...existing,
                critique_iterations: event.iterations as number,
                quality_score: event.quality_score as number,
                critique_history: [...existing.critique_history, event.critique as Parameters<typeof upsertAgent>[0]["critique_history"][0]],
              });
            }
          }
          break;
      }
    };

    return () => socket.close();
  }, [sessionId]);

  return ws;
}
```

- [ ] **Step 5: Create frontend/src/components/PhaseIndicator.tsx**
```tsx
import type { Phase } from "../types";

const PHASE_CONFIG: Record<Phase, { label: string; color: string; description: string }> = {
  DESIGN: { label: "DESIGN TIME", color: "bg-blue-600", description: "Building the agent graph" },
  DRYRUN: { label: "DRY RUN", color: "bg-yellow-500", description: "Validating in sandbox" },
  RUN: { label: "RUN TIME", color: "bg-green-600", description: "Executing against real systems" },
  COMPLETED: { label: "COMPLETED", color: "bg-gray-500", description: "All agents completed" },
};

export function PhaseIndicator({ phase }: { phase: Phase }) {
  const cfg = PHASE_CONFIG[phase];
  return (
    <div className={`${cfg.color} text-white px-6 py-2 flex items-center gap-3 font-mono`}>
      <span className="animate-pulse w-2 h-2 rounded-full bg-white inline-block" />
      <span className="font-bold text-sm tracking-widest">[{cfg.label}]</span>
      <span className="text-xs opacity-80">{cfg.description}</span>
    </div>
  );
}
```

- [ ] **Step 6: Create frontend/src/components/CritiquePanel.tsx**
```tsx
import type { CritiqueResult } from "../types";

const VERDICT_COLORS: Record<string, string> = {
  APPROVED: "text-green-400",
  NEEDS_REVISION: "text-yellow-400",
  ESCALATE_AUTO_FIX: "text-orange-400",
  ESCALATE_RETHINK: "text-red-400",
  ESCALATE_USER: "text-red-600",
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-900 text-red-200",
  major: "bg-orange-900 text-orange-200",
  minor: "bg-yellow-900 text-yellow-200",
  informational: "bg-gray-700 text-gray-300",
};

export function CritiquePanel({ critique }: { critique: CritiqueResult }) {
  return (
    <div className="bg-gray-800 border border-gray-600 rounded p-3 text-xs font-mono mt-2">
      <div className="flex justify-between items-center mb-2">
        <span className="text-gray-400">Critique iter {critique.iteration}/{critique.max_iterations}</span>
        <span className={`font-bold ${VERDICT_COLORS[critique.verdict] || "text-white"}`}>
          {critique.verdict}
        </span>
        <span className="text-gray-300">Score: {critique.quality_score}/10</span>
      </div>
      {critique.issues.length > 0 && (
        <div className="space-y-1">
          {critique.issues.map((issue) => (
            <div key={issue.issue_id} className={`px-2 py-1 rounded ${SEVERITY_COLORS[issue.severity]}`}>
              <span className="font-bold">[{issue.severity.toUpperCase()}]</span> {issue.description}
              <div className="text-xs opacity-70 mt-0.5">Fix: {issue.recommendation}</div>
            </div>
          ))}
        </div>
      )}
      {critique.approved_aspects.length > 0 && (
        <div className="mt-2 text-green-400">
          ✓ {critique.approved_aspects.join(" · ")}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 7: Create frontend/src/components/AgentCard.tsx**
```tsx
import { useState } from "react";
import type { AtomicAgent } from "../types";
import { CritiquePanel } from "./CritiquePanel";

const STATE_COLORS: Record<string, string> = {
  PENDING: "bg-gray-600",
  SPECIFYING: "bg-blue-600 animate-pulse",
  DESIGN_CRITIQUE_1: "bg-yellow-600 animate-pulse",
  DESIGN_CRITIQUE_2: "bg-yellow-600 animate-pulse",
  DESIGN_CRITIQUE_3: "bg-yellow-600 animate-pulse",
  DESIGN_CRITIQUE_4: "bg-orange-600 animate-pulse",
  DESIGN_CRITIQUE_5: "bg-red-600 animate-pulse",
  APPROVED: "bg-green-600",
  COMPLETED: "bg-green-700",
  FAILED_ESCALATED: "bg-red-700",
  USER_ESCALATED: "bg-purple-600",
  REVISING_SPEC: "bg-blue-500 animate-pulse",
};

export function AgentCard({ agent }: { agent: AtomicAgent }) {
  const [showCritique, setShowCritique] = useState(false);
  const stateColor = STATE_COLORS[agent.state] || "bg-gray-700";
  const latestCritique = agent.critique_history[agent.critique_history.length - 1];

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 font-mono">
      <div className="flex justify-between items-start">
        <div>
          <div className="text-white font-bold text-sm">{agent.agent_name}</div>
          <div className="text-gray-400 text-xs mt-0.5">{agent.description}</div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className={`${stateColor} text-white text-xs px-2 py-0.5 rounded`}>
            {agent.state}
          </span>
          {agent.quality_score !== null && (
            <span className="text-green-400 text-xs">★ {agent.quality_score}/10</span>
          )}
        </div>
      </div>

      {agent.critique_iterations > 0 && (
        <div className="mt-2 text-xs text-gray-500">
          Critique: {agent.critique_iterations}/5 iterations
          {latestCritique && (
            <button
              className="ml-2 text-blue-400 underline"
              onClick={() => setShowCritique((v) => !v)}
            >
              {showCritique ? "hide" : "show details"}
            </button>
          )}
        </div>
      )}

      {showCritique && latestCritique && <CritiquePanel critique={latestCritique} />}
    </div>
  );
}
```

- [ ] **Step 8: Create frontend/src/components/DAGVisualization.tsx**
```tsx
import ReactFlow, { Controls, Background, MiniMap, type Node, type Edge } from "reactflow";
import "reactflow/dist/style.css";
import type { DAGData, AtomicAgent } from "../types";

const STATE_NODE_COLORS: Record<string, string> = {
  PENDING: "#374151",
  SPECIFYING: "#1d4ed8",
  APPROVED: "#16a34a",
  COMPLETED: "#15803d",
  FAILED_ESCALATED: "#dc2626",
  USER_ESCALATED: "#7c3aed",
};

interface Props {
  dag: DAGData;
  agents: Record<string, AtomicAgent>;
}

export function DAGVisualization({ dag, agents }: Props) {
  const agentByNodeId = Object.fromEntries(
    dag.nodes.map((n) => [n.node_id, agents[n.agent_id]])
  );

  const rfNodes: Node[] = dag.nodes.map((n, i) => {
    const agent = agentByNodeId[n.node_id];
    const state = agent?.state || "PENDING";
    return {
      id: n.node_id,
      position: { x: (i % 3) * 250, y: Math.floor(i / 3) * 120 },
      data: { label: n.agent_name },
      style: {
        background: STATE_NODE_COLORS[state] || "#374151",
        color: "white",
        border: "1px solid #4b5563",
        borderRadius: 8,
        fontSize: 12,
        fontFamily: "monospace",
        padding: "8px 12px",
      },
    };
  });

  const rfEdges: Edge[] = dag.edges.map((e) => ({
    id: e.edge_id,
    source: e.from_node,
    target: e.to_node,
    style: { stroke: "#6b7280" },
    animated: true,
  }));

  return (
    <div className="w-full h-96 bg-gray-950 rounded-lg border border-gray-700">
      <ReactFlow nodes={rfNodes} edges={rfEdges} fitView>
        <Controls />
        <MiniMap />
        <Background color="#1f2937" gap={16} />
      </ReactFlow>
    </div>
  );
}
```

- [ ] **Step 9: Create frontend/src/components/ExecutionLog.tsx**
```tsx
import { useRef, useEffect } from "react";
import type { WSEvent } from "../types";

const EVENT_COLORS: Record<string, string> = {
  SESSION_STARTED: "text-blue-400",
  PHASE_UPDATE: "text-cyan-400",
  AGENT_STARTED: "text-yellow-300",
  AGENT_PRODUCED: "text-green-300",
  CRITIQUE_COMPLETE: "text-purple-300",
  AGENT_STATE_CHANGE: "text-orange-300",
  SESSION_COMPLETED: "text-green-500 font-bold",
  ERROR: "text-red-400 font-bold",
  LIBRARY_RESULTS: "text-gray-400",
};

export function ExecutionLog({ events }: { events: WSEvent[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  return (
    <div className="bg-gray-950 border border-gray-700 rounded-lg h-64 overflow-y-auto p-3 font-mono text-xs">
      {[...events].reverse().map((e, i) => (
        <div key={i} className={`${EVENT_COLORS[e.type] || "text-gray-300"} mb-0.5`}>
          <span className="text-gray-600">[{e.type}]</span>{" "}
          {e.message as string || e.agent_name as string || e.phase as string || ""}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
```

- [ ] **Step 10: Create frontend/src/components/LibraryBrowser.tsx**
```tsx
import type { LibraryPattern } from "../types";

export function LibraryBrowser({ patterns }: { patterns: LibraryPattern[] }) {
  if (patterns.length === 0) return null;
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 font-mono">
      <div className="text-cyan-400 font-bold text-sm mb-2">
        [LIBRARY] Found {patterns.length} matching patterns
      </div>
      <div className="space-y-2">
        {patterns.map((p, i) => (
          <div key={p.id} className="flex justify-between text-xs border-b border-gray-700 pb-1">
            <span className="text-gray-300">
              <span className="text-yellow-400">#{i + 1}</span> {p.name}
            </span>
            <span className="text-gray-500">{p.domain}</span>
            <span className="text-green-400">★ {p.quality_score}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 11: Create frontend/src/components/InputCollector.tsx**
```tsx
import { useState } from "react";
import { provideInput } from "../api/client";

interface InputRequest {
  input_name: string;
  description: string;
  type: string;
  required: boolean;
}

interface Props {
  sessionId: string;
  requests: InputRequest[];
  onSubmit: () => void;
}

export function InputCollector({ sessionId, requests, onSubmit }: Props) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  if (requests.length === 0) return null;

  const handleSubmit = async () => {
    setSubmitting(true);
    for (const req of requests) {
      if (values[req.input_name]) {
        await provideInput(sessionId, req.input_name, values[req.input_name]);
      }
    }
    setSubmitting(false);
    onSubmit();
  };

  return (
    <div className="bg-yellow-950 border border-yellow-700 rounded-lg p-4 font-mono">
      <div className="text-yellow-400 font-bold mb-3">[INPUT] INPUT REQUIRED</div>
      {requests.map((req) => (
        <div key={req.input_name} className="mb-3">
          <label className="block text-yellow-200 text-sm mb-1">
            {req.input_name}
            {req.required && <span className="text-red-400 ml-1">*</span>}
            <span className="text-gray-400 ml-2 text-xs">({req.type})</span>
          </label>
          <div className="text-gray-400 text-xs mb-1">{req.description}</div>
          <input
            className="w-full bg-gray-900 border border-gray-600 text-white px-3 py-1.5 rounded text-sm"
            value={values[req.input_name] || ""}
            onChange={(e) => setValues((v) => ({ ...v, [req.input_name]: e.target.value }))}
          />
        </div>
      ))}
      <button
        className="bg-yellow-600 hover:bg-yellow-500 text-black font-bold px-4 py-2 rounded text-sm"
        onClick={handleSubmit}
        disabled={submitting}
      >
        {submitting ? "Submitting..." : "Submit Inputs"}
      </button>
    </div>
  );
}
```

- [ ] **Step 12: Create frontend/src/pages/Home.tsx**
```tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createSession, listLibrary } from "../api/client";
import { LibraryBrowser } from "../components/LibraryBrowser";
import { useEffect } from "react";
import type { LibraryPattern } from "../types";

export function Home() {
  const [objective, setObjective] = useState("");
  const [loading, setLoading] = useState(false);
  const [library, setLibrary] = useState<LibraryPattern[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    listLibrary().then((r) => setLibrary(r.data)).catch(() => {});
  }, []);

  const handleStart = async () => {
    if (!objective.trim()) return;
    setLoading(true);
    const { data } = await createSession(objective);
    navigate(`/session/${data.session_id}`);
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col items-center justify-center px-4 font-mono">
      <div className="w-full max-w-2xl">
        <h1 className="text-3xl font-bold text-center mb-2 text-cyan-400">AgentMaster</h1>
        <p className="text-gray-400 text-center text-sm mb-8">
          Autonomous Agentic Graph Framework — describe any objective, watch it execute.
        </p>
        <div className="bg-gray-900 border border-gray-700 rounded-lg p-6">
          <label className="block text-sm text-gray-300 mb-2">Your Objective</label>
          <textarea
            className="w-full bg-gray-800 border border-gray-600 text-white px-4 py-3 rounded-lg text-sm resize-none focus:outline-none focus:border-cyan-500"
            rows={4}
            placeholder="Describe any objective... e.g. 'Analyze my GitHub repo for security issues' or 'Automate my weekly reporting workflow'"
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
          />
          <button
            className="mt-4 w-full bg-cyan-600 hover:bg-cyan-500 text-white font-bold py-3 rounded-lg text-sm transition-colors disabled:opacity-50"
            onClick={handleStart}
            disabled={loading || !objective.trim()}
          >
            {loading ? "Initializing..." : "→ Launch AgentMaster"}
          </button>
        </div>
        {library.length > 0 && (
          <div className="mt-6">
            <LibraryBrowser patterns={library} />
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 13: Create frontend/src/pages/Session.tsx**
```tsx
import { useParams } from "react-router-dom";
import { useSessionStore } from "../store/sessionStore";
import { useWebSocket } from "../hooks/useWebSocket";
import { PhaseIndicator } from "../components/PhaseIndicator";
import { AgentCard } from "../components/AgentCard";
import { DAGVisualization } from "../components/DAGVisualization";
import { ExecutionLog } from "../components/ExecutionLog";
import { LibraryBrowser } from "../components/LibraryBrowser";

export function Session() {
  const { sessionId } = useParams<{ sessionId: string }>();
  useWebSocket(sessionId || null);

  const { phase, agents, dag, events, libraryResults, objective, isConnected } =
    useSessionStore();

  const agentList = Object.values(agents);

  return (
    <div className="min-h-screen bg-gray-950 text-white font-mono">
      <PhaseIndicator phase={phase} />

      <div className="px-4 py-3 border-b border-gray-800 flex justify-between text-xs">
        <span className="text-gray-300 truncate max-w-lg">{objective}</span>
        <span className={`${isConnected ? "text-green-400" : "text-red-400"}`}>
          {isConnected ? "● LIVE" : "○ DISCONNECTED"}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-4 p-4">
        {/* Left: Agent Cards */}
        <div className="col-span-1 space-y-2">
          <div className="text-xs text-gray-500 mb-2">AGENTS ({agentList.length})</div>
          {agentList.length === 0 && (
            <div className="text-gray-600 text-xs text-center py-8">
              Waiting for AgentMaster to design blueprint...
            </div>
          )}
          {agentList.map((a) => <AgentCard key={a.agent_id} agent={a} />)}
        </div>

        {/* Center: DAG + Library */}
        <div className="col-span-1 space-y-4">
          <div className="text-xs text-gray-500">DAG VISUALIZATION</div>
          {dag ? (
            <DAGVisualization dag={dag} agents={agents} />
          ) : (
            <div className="h-96 bg-gray-900 border border-gray-700 rounded-lg flex items-center justify-center text-gray-600 text-xs">
              DAG will appear here...
            </div>
          )}
          {libraryResults.length > 0 && <LibraryBrowser patterns={libraryResults} />}
        </div>

        {/* Right: Execution Log */}
        <div className="col-span-1 space-y-2">
          <div className="text-xs text-gray-500">EXECUTION LOG</div>
          <ExecutionLog events={events} />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 14: Update frontend/src/App.tsx**
```tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Home } from "./pages/Home";
import { Session } from "./pages/Session";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/session/:sessionId" element={<Session />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
```

- [ ] **Step 15: Install react-router-dom**
```bash
cd frontend
npm install react-router-dom reactflow
```

- [ ] **Step 16: Commit**
```bash
git add frontend/src/
git commit -m "feat: add React frontend with DAG visualization, phase indicator, agent cards, execution log"
```

---

### Task 9: Configuration Files + README

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `backend/.env.example`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/index.html`
- Modify: `frontend/vite.config.ts`

- [ ] **Step 1: Create .gitignore**
```gitignore
# Python
__pycache__/
*.pyc
*.pyo
.venv/
*.egg-info/
dist/
.env
*.db

# Node
node_modules/
dist/
.env.local

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
```

- [ ] **Step 2: Create backend/.env.example**
```
OPENAI_API_KEY=sk-your-key-here
DATABASE_URL=sqlite:///./agentmaster.db
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=["http://localhost:5173"]
```

- [ ] **Step 3: Update frontend/vite.config.ts with proxy**
```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});
```

- [ ] **Step 4: Create README.md**

See full README content — covers: project overview, architecture diagram, setup instructions (backend + frontend), environment variables, running the app, usage, Agent Library, and contributing.

- [ ] **Step 5: Commit**
```bash
git add .gitignore README.md backend/.env.example frontend/vite.config.ts
git commit -m "docs: add README, .gitignore, env example, vite proxy config"
git push origin main
```

---

### Task 10: Integration Test + Final Push

**Files:**
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_integration.py`

- [ ] **Step 1: Create conftest.py**
```python
# backend/tests/conftest.py
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
```

- [ ] **Step 2: Run all backend tests**
```bash
cd backend
.venv\Scripts\activate
pytest tests/ -v --tb=short
```
Expected: All tests pass (at minimum: test_models, test_dag, test_lifecycle, test_library, test_api, test_critique_loop)

- [ ] **Step 3: Start backend and verify health**
```bash
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
# In separate terminal:
curl http://localhost:8000/health
```
Expected: `{"status":"ok","version":"1.0.0"}`

- [ ] **Step 4: Start frontend and verify it loads**
```bash
cd frontend
npm run dev
# Visit http://localhost:5173
```
Expected: Home page loads with objective textarea

- [ ] **Step 5: Final commit and push**
```bash
git add .
git commit -m "feat: complete AgentMaster AAGF implementation — full-stack multi-agent DAG orchestration system"
git push origin main
```

- [ ] **Step 6: Create GitHub release**
```bash
gh release create v1.0.0 --title "AgentMaster v1.0.0" --notes "Initial release of the Autonomous Agentic Graph Framework (AAGF). Full-stack implementation with AgentMaster, AgentProducer, AgentCritique agents, DAG execution engine, WebSocket streaming, React frontend with live DAG visualization, and Agent Library persistence."
```
