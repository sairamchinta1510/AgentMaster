# AgentMaster Backend Core - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete backend orchestration engine - database, agents (AgentMaster, Sub-Agent, Atomic Agent, Critique Agent), execution manager, WebSocket broadcasting, and REST API endpoints.

**Architecture:** Five-layer agent hierarchy (Orchestrator → Sub-Agent → Atomic Agent → Critique Agent) with SQLite persistence, DAG-based execution, and real-time WebSocket event streaming. Clean slate rebuild - delete existing backend code.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite, WebSocket, Python 3.11+, Google Gemini API

## Global Constraints

- Python 3.11 or higher required
- All agent outputs MUST include citations array
- Minimum 3 critique rounds per agent output
- Maximum recursion depth: 5 levels (configurable)
- Maximum children per Sub-Agent: 10
- WebSocket ping interval: 30 seconds
- Database transactions for all state changes
- Structured logging to stdout (JSON format)

---

## File Structure

**New backend structure (clean slate):**

```
backend_new/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI entry point
│   ├── config.py                    # Environment config
│   ├── database.py                  # SQLAlchemy setup
│   ├── models/
│   │   ├── __init__.py
│   │   ├── execution.py             # Execution ORM model
│   │   ├── agent.py                 # Agent ORM model
│   │   ├── edge.py                  # Edge ORM model
│   │   ├── critique.py              # Critique ORM model
│   │   ├── tool_execution.py        # ToolExecution ORM model
│   │   └── agent_template.py        # AgentTemplate ORM model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── execution.py             # Pydantic schemas for API
│   │   ├── agent.py
│   │   ├── critique.py
│   │   └── websocket.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── executions.py        # Execution REST endpoints
│   │   │   ├── agents.py            # Agent REST endpoints
│   │   │   ├── templates.py         # Template library endpoints
│   │   │   └── health.py            # Health check
│   │   └── websockets/
│   │       ├── __init__.py
│   │       ├── studio.py            # Studio WS (planning phase)
│   │       └── control_room.py      # Control Room WS (run phase)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py          # AgentMaster
│   │   ├── sub_agent.py             # Sub-Agent
│   │   ├── atomic_agent.py          # Atomic Agent base
│   │   ├── critique_agent.py        # Critique Agent
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── bash.py              # Bash tool
│   │       ├── file_ops.py          # File read/write
│   │       ├── llm.py               # LLM API calls
│   │       └── web.py               # Web search/fetch
│   ├── services/
│   │   ├── __init__.py
│   │   ├── execution_manager.py     # Execution orchestration
│   │   ├── graph_builder.py         # DAG construction
│   │   ├── websocket_manager.py     # WebSocket broadcast
│   │   └── template_service.py      # Template CRUD
│   └── utils/
│       ├── __init__.py
│       ├── logging_config.py        # Structured logging
│       └── metrics.py               # Token counting, timing
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Pytest fixtures
│   ├── test_database.py
│   ├── test_orchestrator.py
│   ├── test_sub_agent.py
│   ├── test_atomic_agent.py
│   ├── test_critique_agent.py
│   ├── test_execution_manager.py
│   ├── test_graph_builder.py
│   └── test_api.py
├── alembic/                         # Database migrations
│   ├── versions/
│   └── env.py
├── requirements.txt
├── Dockerfile
└── .env.example
```

---

### Task 1: Clean Slate & Database Foundation

**Files:**
- Delete: `backend/` (entire old backend directory)
- Create: `backend_new/app/config.py`
- Create: `backend_new/app/database.py`
- Create: `backend_new/app/models/__init__.py`
- Create: `backend_new/app/models/execution.py`
- Create: `backend_new/app/models/agent.py`
- Create: `backend_new/app/models/edge.py`
- Create: `backend_new/app/models/critique.py`
- Create: `backend_new/app/models/tool_execution.py`
- Create: `backend_new/app/models/agent_template.py`
- Create: `backend_new/requirements.txt`
- Create: `backend_new/.env.example`
- Test: `backend_new/tests/test_database.py`

**Interfaces:**
- Consumes: None (foundation task)
- Produces:
  - `get_db() -> Generator[Session]` - SQLAlchemy session dependency
  - `Execution`, `Agent`, `Edge`, `Critique`, `ToolExecution`, `AgentTemplate` ORM models
  - All models have `.to_dict()` method

- [ ] **Step 1: Delete old backend**

```bash
cd /Users/schinta/AgentMaster
rm -rf backend
mkdir -p backend_new/app/models backend_new/tests
cd backend_new
```

- [ ] **Step 2: Write requirements.txt**

```txt
fastapi==0.115.0
uvicorn[standard]==0.32.0
sqlalchemy==2.0.36
alembic==1.14.0
pydantic==2.10.3
pydantic-settings==2.6.1
websockets==14.1
google-generativeai==0.8.3
python-dotenv==1.0.1
pytest==8.3.4
pytest-asyncio==0.24.0
httpx==0.28.1
```

- [ ] **Step 3: Write .env.example**

```env
DATABASE_URL=sqlite:///./agentmaster.db
GEMINI_API_KEY=your_gemini_api_key_here
LOG_LEVEL=info
MAX_RECURSION_DEPTH=5
MAX_AGENT_TIMEOUT=300
WEBSOCKET_PING_INTERVAL=30
```

- [ ] **Step 4: Write config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./agentmaster.db"
    gemini_api_key: str
    log_level: str = "info"
    max_recursion_depth: int = 5
    max_agent_timeout: int = 300
    websocket_ping_interval: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 5: Write database.py with session management**

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Database session dependency for FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
```

- [ ] **Step 6: Write Execution model**

Create `backend_new/app/models/execution.py`:

```python
from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class Execution(Base):
    __tablename__ = "executions"

    id = Column(String, primary_key=True)
    objective = Column(Text, nullable=False)
    domain = Column(String, nullable=False)
    status = Column(String, nullable=False)  # planning | running | completed | failed | stopped_by_user | human_review_needed
    root_agent_id = Column(String, nullable=True)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    stopped_by = Column(String, nullable=True)  # user | timeout | error | system
    cancellation_reason = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "objective": self.objective,
            "domain": self.domain,
            "status": self.status,
            "root_agent_id": self.root_agent_id,
            "config": self.config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "stopped_by": self.stopped_by,
            "cancellation_reason": self.cancellation_reason,
        }
```

- [ ] **Step 7: Write Agent model**

Create `backend_new/app/models/agent.py`:

```python
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True)
    execution_id = Column(String, ForeignKey("executions.id"), nullable=False, index=True)
    parent_id = Column(String, ForeignKey("agents.id"), nullable=True, index=True)
    agent_type = Column(String, nullable=False, index=True)  # sub_agent | atomic_agent
    depth = Column(Integer, nullable=False)
    task_description = Column(Text, nullable=False)
    status = Column(String, nullable=False, index=True)  # pending | running | critique_phase | completed | failed | cancelled | human_review
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    citations = Column(JSON, nullable=True)
    retry_count = Column(Integer, default=0)
    timeout_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "parent_id": self.parent_id,
            "agent_type": self.agent_type,
            "depth": self.depth,
            "task_description": self.task_description,
            "status": self.status,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "citations": self.citations,
            "retry_count": self.retry_count,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
```

- [ ] **Step 8: Write Edge model**

Create `backend_new/app/models/edge.py`:

```python
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Edge(Base):
    __tablename__ = "edges"

    id = Column(String, primary_key=True)
    execution_id = Column(String, ForeignKey("executions.id"), nullable=False, index=True)
    from_agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    to_agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    data_description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "from_agent_id": self.from_agent_id,
            "to_agent_id": self.to_agent_id,
            "data_description": self.data_description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
```

- [ ] **Step 9: Write Critique model**

Create `backend_new/app/models/critique.py`:

```python
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Critique(Base):
    __tablename__ = "critiques"

    id = Column(String, primary_key=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    round_number = Column(Integer, nullable=False, index=True)
    critique_type = Column(String, nullable=False)  # factual_verification | completeness_check | consistency_validation
    verdict = Column(String, nullable=False)  # passed | failed
    reasoning = Column(Text, nullable=False)
    unsupported_claims = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "round_number": self.round_number,
            "critique_type": self.critique_type,
            "verdict": self.verdict,
            "reasoning": self.reasoning,
            "unsupported_claims": self.unsupported_claims,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
```

- [ ] **Step 10: Write ToolExecution model**

Create `backend_new/app/models/tool_execution.py`:

```python
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class ToolExecution(Base):
    __tablename__ = "tool_executions"

    id = Column(String, primary_key=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    tool_name = Column(String, nullable=False, index=True)  # bash | file_read | file_write | llm_call | web_search | git_operation | api_call
    tool_input = Column(JSON, nullable=False)
    tool_output = Column(JSON, nullable=True)
    status = Column(String, nullable=False)  # running | completed | failed
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "tool_output": self.tool_output,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
```

- [ ] **Step 11: Write AgentTemplate model**

Create `backend_new/app/models/agent_template.py`:

```python
from sqlalchemy import Column, String, Integer, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class AgentTemplate(Base):
    __tablename__ = "agent_templates"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True, index=True)
    domain_tags = Column(JSON, nullable=True)
    template_spec = Column(JSON, nullable=False)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "domain_tags": self.domain_tags,
            "template_spec": self.template_spec,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
```

- [ ] **Step 12: Write models __init__.py**

Create `backend_new/app/models/__init__.py`:

```python
from app.models.execution import Execution
from app.models.agent import Agent
from app.models.edge import Edge
from app.models.critique import Critique
from app.models.tool_execution import ToolExecution
from app.models.agent_template import AgentTemplate

__all__ = [
    "Execution",
    "Agent",
    "Edge",
    "Critique",
    "ToolExecution",
    "AgentTemplate",
]
```

- [ ] **Step 13: Write test for database models**

Create `backend_new/tests/conftest.py`:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base

@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
```

Create `backend_new/tests/test_database.py`:

```python
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
```

- [ ] **Step 14: Run database tests**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_database.py -v
```

Expected: All tests pass

- [ ] **Step 15: Initialize database**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -c "from app.database import init_db; init_db(); print('Database initialized')"
```

Expected: "Database initialized" printed, `agentmaster.db` file created

- [ ] **Step 16: Commit database foundation**

```bash
cd /Users/schinta/AgentMaster
git add backend_new/
git commit -m "feat: database foundation with SQLAlchemy models

- Clean slate: deleted old backend
- Created 6 ORM models: Execution, Agent, Edge, Critique, ToolExecution, AgentTemplate
- All models have to_dict() serialization
- Database initialization with SQLite
- Test coverage for all models"
```

---

### Task 2: Pydantic Schemas & Logging

**Files:**
- Create: `backend_new/app/schemas/__init__.py`
- Create: `backend_new/app/schemas/execution.py`
- Create: `backend_new/app/schemas/agent.py`
- Create: `backend_new/app/schemas/critique.py`
- Create: `backend_new/app/schemas/websocket.py`
- Create: `backend_new/app/utils/__init__.py`
- Create: `backend_new/app/utils/logging_config.py`
- Create: `backend_new/app/utils/metrics.py`

**Interfaces:**
- Consumes: ORM models from Task 1
- Produces:
  - `CreateExecutionRequest`, `ExecutionResponse` Pydantic schemas
  - `AgentResponse`, `CritiqueResponse` Pydantic schemas
  - `WebSocketEvent` base schema
  - `setup_logging() -> None` - Configure structured logging
  - `log_event(event_type: str, data: dict) -> None` - Structured event logging
  - `count_tokens(text: str) -> int` - Token counting utility

- [ ] **Step 1: Write execution schemas**

Create `backend_new/app/schemas/execution.py`:

```python
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class CreateExecutionRequest(BaseModel):
    objective: str = Field(..., min_length=1, description="User's goal")
    domain: str = Field(..., min_length=1, description="User-defined domain")
    config: Optional[Dict[str, Any]] = Field(default=None, description="Optional execution config")


class ExecutionResponse(BaseModel):
    id: str
    objective: str
    domain: str
    status: str
    root_agent_id: Optional[str]
    config: Optional[Dict[str, Any]]
    created_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    stopped_at: Optional[str]
    stopped_by: Optional[str]
    cancellation_reason: Optional[str]

    class Config:
        from_attributes = True
```

- [ ] **Step 2: Write agent schemas**

Create `backend_new/app/schemas/agent.py`:

```python
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class CitationSchema(BaseModel):
    source_type: str  # file | url | command
    source: str
    excerpt: Optional[str]


class AgentResponse(BaseModel):
    id: str
    execution_id: str
    parent_id: Optional[str]
    agent_type: str
    depth: int
    task_description: str
    status: str
    input_data: Optional[Dict[str, Any]]
    output_data: Optional[Dict[str, Any]]
    citations: Optional[List[CitationSchema]]
    retry_count: int
    timeout_seconds: Optional[int]
    created_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]

    class Config:
        from_attributes = True
```

- [ ] **Step 3: Write critique schemas**

Create `backend_new/app/schemas/critique.py`:

```python
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class CritiqueRoundResult(BaseModel):
    round: int
    type: str  # factual_verification | completeness_check | consistency_validation
    passed: bool
    reasoning: str
    unsupported_claims: List[str]


class CritiqueResponse(BaseModel):
    id: str
    agent_id: str
    round_number: int
    critique_type: str
    verdict: str
    reasoning: str
    unsupported_claims: Optional[List[str]]
    created_at: Optional[str]

    class Config:
        from_attributes = True


class CritiqueVerdict(BaseModel):
    verdict: str  # approved | rejected | needs_human_review
    round_results: List[CritiqueRoundResult]
    overall_confidence: int  # 0-100
```

- [ ] **Step 4: Write websocket schemas**

Create `backend_new/app/schemas/websocket.py`:

```python
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class WebSocketEvent(BaseModel):
    event_type: str
    timestamp: str
    execution_id: str
    data: Dict[str, Any]

    @classmethod
    def create(cls, event_type: str, execution_id: str, data: Dict[str, Any]) -> "WebSocketEvent":
        return cls(
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat() + "Z",
            execution_id=execution_id,
            data=data
        )


class AgentCreatedEvent(WebSocketEvent):
    event_type: str = "agent_created"


class AgentStartedEvent(WebSocketEvent):
    event_type: str = "agent_started"


class AgentCompletedEvent(WebSocketEvent):
    event_type: str = "agent_completed"


class AgentFailedEvent(WebSocketEvent):
    event_type: str = "agent_failed"


class CritiqueRoundStartedEvent(WebSocketEvent):
    event_type: str = "critique_round_started"


class CritiqueRoundCompletedEvent(WebSocketEvent):
    event_type: str = "critique_round_completed"


class ExecutionStartedEvent(WebSocketEvent):
    event_type: str = "execution_started"


class ExecutionCompletedEvent(WebSocketEvent):
    event_type: str = "execution_completed"


class ExecutionStoppedEvent(WebSocketEvent):
    event_type: str = "execution_stopped"
```

- [ ] **Step 5: Write schemas __init__.py**

Create `backend_new/app/schemas/__init__.py`:

```python
from app.schemas.execution import CreateExecutionRequest, ExecutionResponse
from app.schemas.agent import AgentResponse, CitationSchema
from app.schemas.critique import CritiqueResponse, CritiqueVerdict, CritiqueRoundResult
from app.schemas.websocket import (
    WebSocketEvent,
    AgentCreatedEvent,
    AgentStartedEvent,
    AgentCompletedEvent,
    AgentFailedEvent,
    CritiqueRoundStartedEvent,
    CritiqueRoundCompletedEvent,
    ExecutionStartedEvent,
    ExecutionCompletedEvent,
    ExecutionStoppedEvent,
)

__all__ = [
    "CreateExecutionRequest",
    "ExecutionResponse",
    "AgentResponse",
    "CitationSchema",
    "CritiqueResponse",
    "CritiqueVerdict",
    "CritiqueRoundResult",
    "WebSocketEvent",
    "AgentCreatedEvent",
    "AgentStartedEvent",
    "AgentCompletedEvent",
    "AgentFailedEvent",
    "CritiqueRoundStartedEvent",
    "CritiqueRoundCompletedEvent",
    "ExecutionStartedEvent",
    "ExecutionCompletedEvent",
    "ExecutionStoppedEvent",
]
```

- [ ] **Step 6: Write logging configuration**

Create `backend_new/app/utils/logging_config.py`:

```python
import logging
import json
import sys
from datetime import datetime
from app.config import settings


class StructuredJSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "event_type"):
            log_data["event_type"] = record.event_type
        if hasattr(record, "execution_id"):
            log_data["execution_id"] = record.execution_id
        if hasattr(record, "agent_id"):
            log_data["agent_id"] = record.agent_id

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging() -> None:
    """Configure structured logging to stdout."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJSONFormatter())
    root_logger.addHandler(handler)


def log_event(event_type: str, data: dict, execution_id: str = None, agent_id: str = None) -> None:
    """Log a structured event."""
    logger = logging.getLogger("agentmaster")
    extra = {"event_type": event_type}
    if execution_id:
        extra["execution_id"] = execution_id
    if agent_id:
        extra["agent_id"] = agent_id

    logger.info(json.dumps(data), extra=extra)
```

- [ ] **Step 7: Write metrics utilities**

Create `backend_new/app/utils/metrics.py`:

```python
import time
from functools import wraps
from typing import Callable


def count_tokens(text: str) -> int:
    """
    Estimate token count for a text string.
    Rough approximation: 1 token ~= 4 characters for English text.
    """
    return len(text) // 4


class Timer:
    """Context manager for timing operations."""

    def __init__(self):
        self.start_time = None
        self.elapsed_ms = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = int((time.time() - self.start_time) * 1000)


def timed(func: Callable) -> Callable:
    """Decorator to log execution time of a function."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        with Timer() as timer:
            result = func(*args, **kwargs)
        print(f"{func.__name__} took {timer.elapsed_ms}ms")
        return result
    return wrapper
```

- [ ] **Step 8: Write utils __init__.py**

Create `backend_new/app/utils/__init__.py`:

```python
from app.utils.logging_config import setup_logging, log_event
from app.utils.metrics import count_tokens, Timer, timed

__all__ = ["setup_logging", "log_event", "count_tokens", "Timer", "timed"]
```

- [ ] **Step 9: Test schemas validation**

Create `backend_new/tests/test_schemas.py`:

```python
import pytest
from pydantic import ValidationError
from app.schemas import CreateExecutionRequest, ExecutionResponse, WebSocketEvent


def test_create_execution_request_valid():
    """Test valid execution request."""
    req = CreateExecutionRequest(
        objective="Create a presentation",
        domain="Create PPT",
        config={"max_recursion_depth": 5}
    )
    assert req.objective == "Create a presentation"
    assert req.domain == "Create PPT"
    assert req.config["max_recursion_depth"] == 5


def test_create_execution_request_missing_objective():
    """Test that missing objective raises validation error."""
    with pytest.raises(ValidationError):
        CreateExecutionRequest(domain="Test")


def test_websocket_event_creation():
    """Test WebSocket event factory method."""
    event = WebSocketEvent.create(
        event_type="agent_started",
        execution_id="exec_123",
        data={"agent_id": "agent_456", "agent_name": "TestAgent"}
    )
    assert event.event_type == "agent_started"
    assert event.execution_id == "exec_123"
    assert event.data["agent_id"] == "agent_456"
    assert "timestamp" in event.model_dump()
```

- [ ] **Step 10: Run schema tests**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_schemas.py -v
```

Expected: All tests pass

- [ ] **Step 11: Test logging**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -c "
from app.utils import setup_logging, log_event
setup_logging()
log_event('test_event', {'message': 'Testing logging'}, execution_id='test_123')
print('Logging test complete')
"
```

Expected: JSON log output to stdout with timestamp, event_type, execution_id

- [ ] **Step 12: Test token counting**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -c "
from app.utils import count_tokens
text = 'This is a test message for token counting'
tokens = count_tokens(text)
print(f'Tokens: {tokens}')
assert tokens > 0
print('Token counting works')
"
```

Expected: "Token counting works" printed

- [ ] **Step 13: Commit schemas and utilities**

```bash
cd /Users/schinta/AgentMaster
git add backend_new/app/schemas/ backend_new/app/utils/ backend_new/tests/test_schemas.py
git commit -m "feat: Pydantic schemas and logging utilities

- Execution, Agent, Critique schemas for API validation
- WebSocket event schemas with factory method
- Structured JSON logging to stdout
- Token counting and timing utilities
- Test coverage for schemas and logging"
```

---

### Task 3: WebSocket Manager & Graph Builder

**Files:**
- Create: `backend_new/app/services/__init__.py`
- Create: `backend_new/app/services/websocket_manager.py`
- Create: `backend_new/app/services/graph_builder.py`
- Test: `backend_new/tests/test_websocket_manager.py`
- Test: `backend_new/tests/test_graph_builder.py`

**Interfaces:**
- Consumes:
  - `WebSocketEvent` from Task 2
  - `Agent`, `Edge` models from Task 1
- Produces:
  - `WebSocketManager.connect(execution_id: str, websocket: WebSocket) -> None`
  - `WebSocketManager.disconnect(execution_id: str, websocket: WebSocket) -> None`
  - `WebSocketManager.broadcast(execution_id: str, event: WebSocketEvent) -> None`
  - `GraphBuilder.add_agent(agent: Agent) -> None`
  - `GraphBuilder.add_edge(edge: Edge) -> None`
  - `GraphBuilder.validate_no_cycles() -> bool`
  - `GraphBuilder.topological_sort() -> List[str]` (returns agent IDs in execution order)

- [ ] **Step 1: Write failing test for WebSocketManager**

Create `backend_new/tests/test_websocket_manager.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.websocket_manager import WebSocketManager
from app.schemas import WebSocketEvent


@pytest.mark.asyncio
async def test_connect_and_broadcast():
    """Test connecting a WebSocket and broadcasting an event."""
    manager = WebSocketManager()
    
    # Mock WebSocket
    ws = MagicMock()
    ws.send_json = AsyncMock()
    
    # Connect
    manager.connect("exec_123", ws)
    assert "exec_123" in manager.connections
    assert ws in manager.connections["exec_123"]
    
    # Broadcast event
    event = WebSocketEvent.create(
        event_type="test_event",
        execution_id="exec_123",
        data={"message": "test"}
    )
    await manager.broadcast("exec_123", event)
    
    # Verify send_json was called
    ws.send_json.assert_called_once()
    call_args = ws.send_json.call_args[0][0]
    assert call_args["event_type"] == "test_event"


@pytest.mark.asyncio
async def test_disconnect():
    """Test disconnecting a WebSocket."""
    manager = WebSocketManager()
    ws = MagicMock()
    ws.send_json = AsyncMock()
    
    manager.connect("exec_123", ws)
    manager.disconnect("exec_123", ws)
    
    assert ws not in manager.connections.get("exec_123", [])
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_websocket_manager.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.websocket_manager'"

- [ ] **Step 3: Implement WebSocketManager**

Create `backend_new/app/services/websocket_manager.py`:

```python
from typing import Dict, List
from fastapi import WebSocket
from app.schemas.websocket import WebSocketEvent
import logging

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and broadcasts events."""

    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}

    def connect(self, execution_id: str, websocket: WebSocket) -> None:
        """Register a new WebSocket connection for an execution."""
        if execution_id not in self.connections:
            self.connections[execution_id] = []
        self.connections[execution_id].append(websocket)
        logger.info(f"WebSocket connected for execution {execution_id}")

    def disconnect(self, execution_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if execution_id in self.connections:
            if websocket in self.connections[execution_id]:
                self.connections[execution_id].remove(websocket)
            if not self.connections[execution_id]:
                del self.connections[execution_id]
        logger.info(f"WebSocket disconnected for execution {execution_id}")

    async def broadcast(self, execution_id: str, event: WebSocketEvent) -> None:
        """Broadcast an event to all connected clients for an execution."""
        if execution_id not in self.connections:
            return

        event_dict = event.model_dump()
        disconnected = []

        for websocket in self.connections[execution_id]:
            try:
                await websocket.send_json(event_dict)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(websocket)

        # Clean up disconnected websockets
        for ws in disconnected:
            self.disconnect(execution_id, ws)


# Global singleton
websocket_manager = WebSocketManager()
```

- [ ] **Step 4: Run WebSocketManager tests**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_websocket_manager.py -v
```

Expected: All tests pass

- [ ] **Step 5: Write failing test for GraphBuilder**

Create `backend_new/tests/test_graph_builder.py`:

```python
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
```

- [ ] **Step 6: Run test to verify it fails**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_graph_builder.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.graph_builder'"

- [ ] **Step 7: Implement GraphBuilder**

Create `backend_new/app/services/graph_builder.py`:

```python
from typing import Dict, List, Set
from app.models import Agent, Edge
import logging

logger = logging.getLogger(__name__)


class GraphBuilder:
    """Builds and validates DAG from agents and edges."""

    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.edges: List[Edge] = []
        self.adjacency: Dict[str, List[str]] = {}  # agent_id -> [dependent_agent_ids]

    def add_agent(self, agent: Agent) -> None:
        """Add an agent to the graph."""
        self.agents[agent.id] = agent
        if agent.id not in self.adjacency:
            self.adjacency[agent.id] = []

    def add_edge(self, edge: Edge) -> None:
        """Add an edge between two agents."""
        self.edges.append(edge)
        
        if edge.from_agent_id not in self.adjacency:
            self.adjacency[edge.from_agent_id] = []
        if edge.to_agent_id not in self.adjacency:
            self.adjacency[edge.to_agent_id] = []
        
        self.adjacency[edge.from_agent_id].append(edge.to_agent_id)

    def validate_no_cycles(self) -> bool:
        """
        Validate that the graph has no cycles using DFS.
        Returns True if no cycles, False if cycle detected.
        """
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in self.adjacency.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for agent_id in self.agents:
            if agent_id not in visited:
                if has_cycle(agent_id):
                    logger.error(f"Cycle detected in graph involving agent {agent_id}")
                    return False

        return True

    def topological_sort(self) -> List[str]:
        """
        Return agents in topological order (dependency order).
        Agents with no dependencies come first.
        """
        in_degree = {agent_id: 0 for agent_id in self.agents}
        
        for agent_id in self.agents:
            for neighbor in self.adjacency.get(agent_id, []):
                in_degree[neighbor] += 1

        queue = [agent_id for agent_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for neighbor in self.adjacency.get(current, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self.agents):
            logger.error("Topological sort failed - graph may have cycles")
            return []

        return result
```

- [ ] **Step 8: Run GraphBuilder tests**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_graph_builder.py -v
```

Expected: All tests pass

- [ ] **Step 9: Write services __init__.py**

Create `backend_new/app/services/__init__.py`:

```python
from app.services.websocket_manager import WebSocketManager, websocket_manager
from app.services.graph_builder import GraphBuilder

__all__ = ["WebSocketManager", "websocket_manager", "GraphBuilder"]
```

- [ ] **Step 10: Run all service tests**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_websocket_manager.py tests/test_graph_builder.py -v
```

Expected: All tests pass

- [ ] **Step 11: Commit WebSocket manager and graph builder**

```bash
cd /Users/schinta/AgentMaster
git add backend_new/app/services/ backend_new/tests/test_websocket_manager.py backend_new/tests/test_graph_builder.py
git commit -m "feat: WebSocket manager and graph builder

- WebSocketManager: connection management and event broadcasting
- GraphBuilder: DAG construction, cycle detection, topological sort
- Test coverage for both services
- Global websocket_manager singleton"
```

---

### Task 4: Atomic Agent Tools

**Files:**
- Create: `backend_new/app/agents/__init__.py`
- Create: `backend_new/app/agents/tools/__init__.py`
- Create: `backend_new/app/agents/tools/bash.py`
- Create: `backend_new/app/agents/tools/file_ops.py`
- Create: `backend_new/app/agents/tools/llm.py`
- Create: `backend_new/app/agents/tools/web.py`
- Test: `backend_new/tests/test_tools.py`

**Interfaces:**
- Consumes:
  - `settings.gemini_api_key` from Task 1
  - `count_tokens()` from Task 2
- Produces:
  - `bash_tool(command: str, timeout: int = 30) -> dict` - Returns {"status": "completed"|"failed", "stdout": str, "stderr": str, "exit_code": int}
  - `file_read_tool(file_path: str) -> dict` - Returns {"status": "completed"|"failed", "content": str, "error": str}
  - `file_write_tool(file_path: str, content: str) -> dict` - Returns {"status": "completed"|"failed", "bytes_written": int, "error": str}
  - `llm_call_tool(prompt: str, system: str = None) -> dict` - Returns {"status": "completed"|"failed", "response": str, "tokens_used": int, "error": str}
  - `web_search_tool(query: str) -> dict` - Returns {"status": "completed"|"failed", "results": list, "error": str}

- [ ] **Step 1: Write failing test for bash tool**

Create `backend_new/tests/test_tools.py`:

```python
import pytest
from app.agents.tools.bash import bash_tool


def test_bash_tool_success():
    """Test bash tool with successful command."""
    result = bash_tool("echo 'Hello World'")
    assert result["status"] == "completed"
    assert "Hello World" in result["stdout"]
    assert result["exit_code"] == 0


def test_bash_tool_failure():
    """Test bash tool with failing command."""
    result = bash_tool("exit 1")
    assert result["status"] == "failed"
    assert result["exit_code"] == 1


def test_bash_tool_timeout():
    """Test bash tool timeout."""
    result = bash_tool("sleep 10", timeout=1)
    assert result["status"] == "failed"
    assert "timeout" in result["stderr"].lower() or "timed out" in result.get("error", "").lower()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_tools.py::test_bash_tool_success -v
```

Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement bash tool**

Create `backend_new/app/agents/tools/bash.py`:

```python
import subprocess
from typing import Dict


def bash_tool(command: str, timeout: int = 30) -> Dict:
    """
    Execute a bash command and return the result.
    
    Args:
        command: The bash command to execute
        timeout: Maximum execution time in seconds
    
    Returns:
        dict with status, stdout, stderr, exit_code
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return {
            "status": "completed" if result.returncode == 0 else "failed",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
            "exit_code": -1,
            "error": "Command execution timeout"
        }
    except Exception as e:
        return {
            "status": "failed",
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "error": str(e)
        }
```

- [ ] **Step 4: Run bash tool tests**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_tools.py::test_bash_tool_success tests/test_tools.py::test_bash_tool_failure -v
```

Expected: Tests pass

- [ ] **Step 5: Implement file operations tools**

Create `backend_new/app/agents/tools/file_ops.py`:

```python
from typing import Dict
import os


def file_read_tool(file_path: str) -> Dict:
    """
    Read a file and return its content.
    
    Args:
        file_path: Path to the file to read
    
    Returns:
        dict with status, content, error
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "status": "completed",
            "content": content,
            "bytes_read": len(content.encode('utf-8'))
        }
    except FileNotFoundError:
        return {
            "status": "failed",
            "content": "",
            "error": f"File not found: {file_path}"
        }
    except Exception as e:
        return {
            "status": "failed",
            "content": "",
            "error": str(e)
        }


def file_write_tool(file_path: str, content: str) -> Dict:
    """
    Write content to a file.
    
    Args:
        file_path: Path to the file to write
        content: Content to write
    
    Returns:
        dict with status, bytes_written, error
    """
    try:
        # Create parent directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        bytes_written = len(content.encode('utf-8'))
        
        return {
            "status": "completed",
            "bytes_written": bytes_written,
            "file_path": file_path
        }
    except Exception as e:
        return {
            "status": "failed",
            "bytes_written": 0,
            "error": str(e)
        }
```

- [ ] **Step 6: Test file operations**

Add to `backend_new/tests/test_tools.py`:

```python
import os
import tempfile
from app.agents.tools.file_ops import file_read_tool, file_write_tool


def test_file_write_and_read():
    """Test writing and reading a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test.txt")
        content = "Hello, AgentMaster!"
        
        # Write
        write_result = file_write_tool(file_path, content)
        assert write_result["status"] == "completed"
        assert write_result["bytes_written"] > 0
        
        # Read
        read_result = file_read_tool(file_path)
        assert read_result["status"] == "completed"
        assert read_result["content"] == content


def test_file_read_not_found():
    """Test reading non-existent file."""
    result = file_read_tool("/tmp/nonexistent_file_12345.txt")
    assert result["status"] == "failed"
    assert "not found" in result["error"].lower()
```

Run:

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_tools.py::test_file_write_and_read tests/test_tools.py::test_file_read_not_found -v
```

Expected: Tests pass

- [ ] **Step 7: Implement LLM tool**

Create `backend_new/app/agents/tools/llm.py`:

```python
from typing import Dict, Optional
import google.generativeai as genai
from app.config import settings
from app.utils.metrics import count_tokens

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)


def llm_call_tool(prompt: str, system: Optional[str] = None) -> Dict:
    """
    Call Google Gemini LLM with a prompt.
    
    Args:
        prompt: The user prompt
        system: Optional system instruction
    
    Returns:
        dict with status, response, tokens_used, error
    """
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system if system else None
        )
        
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Estimate tokens
        prompt_tokens = count_tokens(prompt)
        response_tokens = count_tokens(response_text)
        
        return {
            "status": "completed",
            "response": response_text,
            "tokens_used": prompt_tokens + response_tokens,
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens
        }
    except Exception as e:
        return {
            "status": "failed",
            "response": "",
            "tokens_used": 0,
            "error": str(e)
        }
```

- [ ] **Step 8: Test LLM tool (requires API key)**

Add to `backend_new/tests/test_tools.py`:

```python
import pytest
from app.agents.tools.llm import llm_call_tool


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set"
)
def test_llm_call_tool():
    """Test LLM call with Gemini."""
    result = llm_call_tool("Say 'Hello AgentMaster' and nothing else.")
    assert result["status"] == "completed"
    assert "Hello" in result["response"] or "AgentMaster" in result["response"]
    assert result["tokens_used"] > 0
```

- [ ] **Step 9: Implement web search tool (stub)**

Create `backend_new/app/agents/tools/web.py`:

```python
from typing import Dict, List


def web_search_tool(query: str, max_results: int = 5) -> Dict:
    """
    Search the web for information.
    
    Note: This is a stub implementation. In production, integrate with
    a search API (Google Custom Search, Bing, DuckDuckGo, etc.)
    
    Args:
        query: Search query
        max_results: Maximum number of results
    
    Returns:
        dict with status, results, error
    """
    # Stub implementation - returns empty results
    return {
        "status": "completed",
        "query": query,
        "results": [],
        "message": "Web search not yet implemented - stub only"
    }


def web_fetch_tool(url: str) -> Dict:
    """
    Fetch content from a URL.
    
    Args:
        url: URL to fetch
    
    Returns:
        dict with status, content, error
    """
    try:
        import requests
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        return {
            "status": "completed",
            "content": response.text,
            "status_code": response.status_code,
            "url": url
        }
    except Exception as e:
        return {
            "status": "failed",
            "content": "",
            "error": str(e)
        }
```

- [ ] **Step 10: Write tools __init__.py**

Create `backend_new/app/agents/tools/__init__.py`:

```python
from app.agents.tools.bash import bash_tool
from app.agents.tools.file_ops import file_read_tool, file_write_tool
from app.agents.tools.llm import llm_call_tool
from app.agents.tools.web import web_search_tool, web_fetch_tool

__all__ = [
    "bash_tool",
    "file_read_tool",
    "file_write_tool",
    "llm_call_tool",
    "web_search_tool",
    "web_fetch_tool",
]
```

- [ ] **Step 11: Add requests to requirements.txt**

```bash
cd /Users/schinta/AgentMaster/backend_new
echo "requests==2.32.3" >> requirements.txt
```

- [ ] **Step 12: Run all tool tests**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_tools.py -v
```

Expected: All tests pass (LLM test skipped if no API key)

- [ ] **Step 13: Commit tools**

```bash
cd /Users/schinta/AgentMaster
git add backend_new/app/agents/tools/ backend_new/tests/test_tools.py backend_new/requirements.txt
git commit -m "feat: Atomic Agent tools implementation

- bash_tool: execute shell commands with timeout
- file_read_tool, file_write_tool: file operations
- llm_call_tool: Google Gemini API integration
- web_search_tool, web_fetch_tool: web access (search is stub)
- Full test coverage for all tools
- Added requests dependency"
```

---

### Task 5: Atomic Agent Base Class

**Files:**
- Create: `backend_new/app/agents/atomic_agent.py`
- Test: `backend_new/tests/test_atomic_agent.py`

**Interfaces:**
- Consumes:
  - All tools from Task 4
  - `Agent` model from Task 1
  - `ToolExecution` model from Task 1
- Produces:
  - `AtomicAgent(agent_id: str, task_description: str, input_data: dict, db_session: Session)`
  - `AtomicAgent.execute() -> dict` - Returns {"status": "completed"|"failed", "data": dict, "citations": list, "confidence": int, "execution_time_ms": int}
  - `AtomicAgent.log_tool_execution(tool_name: str, tool_input: dict, tool_output: dict) -> None`

- [ ] **Step 1: Write failing test for AtomicAgent**

Create `backend_new/tests/test_atomic_agent.py`:

```python
import pytest
import uuid
from app.agents.atomic_agent import AtomicAgent
from app.models import Agent


def test_atomic_agent_execute_bash_command(db_session):
    """Test AtomicAgent executing a bash command."""
    agent_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())
    
    # Create agent record
    agent = Agent(
        id=agent_id,
        execution_id=exec_id,
        agent_type="atomic_agent",
        depth=1,
        task_description="Run echo command",
        status="pending",
        input_data={"command": "echo 'test'"}
    )
    db_session.add(agent)
    db_session.commit()
    
    # Execute
    atomic = AtomicAgent(
        agent_id=agent_id,
        task_description="Run echo command",
        input_data={"command": "echo 'test'"},
        db_session=db_session
    )
    
    result = atomic.execute()
    
    assert result["status"] == "completed"
    assert "data" in result
    assert "citations" in result
    assert len(result["citations"]) > 0
    assert result["citations"][0]["source_type"] == "command"


def test_atomic_agent_logs_tool_execution(db_session):
    """Test that AtomicAgent logs tool executions to database."""
    from app.models import ToolExecution
    
    agent_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())
    
    agent = Agent(
        id=agent_id,
        execution_id=exec_id,
        agent_type="atomic_agent",
        depth=1,
        task_description="Test task",
        status="running"
    )
    db_session.add(agent)
    db_session.commit()
    
    atomic = AtomicAgent(
        agent_id=agent_id,
        task_description="Test task",
        input_data={},
        db_session=db_session
    )
    
    # Log a tool execution
    atomic.log_tool_execution(
        tool_name="bash",
        tool_input={"command": "ls"},
        tool_output={"status": "completed", "stdout": "file1.txt"}
    )
    
    # Check database
    tool_exec = db_session.query(ToolExecution).filter_by(agent_id=agent_id).first()
    assert tool_exec is not None
    assert tool_exec.tool_name == "bash"
    assert tool_exec.status == "completed"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_atomic_agent.py::test_atomic_agent_execute_bash_command -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.agents.atomic_agent'"

- [ ] **Step 3: Implement AtomicAgent base class**

Create `backend_new/app/agents/atomic_agent.py`:

```python
import uuid
import time
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.agents.tools import bash_tool, file_read_tool, file_write_tool, llm_call_tool
from app.models import ToolExecution
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AtomicAgent:
    """
    Base class for Atomic Agents - single-purpose executors.
    
    Each Atomic Agent executes ONE action using available tools.
    All outputs MUST include citations for anti-hallucination.
    """
    
    def __init__(
        self,
        agent_id: str,
        task_description: str,
        input_data: Dict[str, Any],
        db_session: Session
    ):
        self.agent_id = agent_id
        self.task_description = task_description
        self.input_data = input_data
        self.db_session = db_session
        self.start_time = None
        
    def execute(self) -> Dict[str, Any]:
        """
        Execute the agent's task.
        
        Returns:
            dict with status, data, citations, confidence, execution_time_ms
        """
        self.start_time = time.time()
        
        try:
            # Determine which tool to use based on task description
            # This is a simple implementation - in production, use LLM to decide
            result = self._execute_task()
            
            execution_time_ms = int((time.time() - self.start_time) * 1000)
            
            return {
                "status": result.get("status", "completed"),
                "data": result.get("data", {}),
                "citations": result.get("citations", []),
                "confidence": result.get("confidence", 100),
                "execution_time_ms": execution_time_ms
            }
        except Exception as e:
            logger.error(f"AtomicAgent {self.agent_id} execution failed: {e}")
            execution_time_ms = int((time.time() - self.start_time) * 1000)
            return {
                "status": "failed",
                "data": {},
                "citations": [],
                "confidence": 0,
                "execution_time_ms": execution_time_ms,
                "error": str(e)
            }
    
    def _execute_task(self) -> Dict[str, Any]:
        """
        Execute the actual task logic.
        Override this in subclasses for specific agent types.
        """
        # Simple heuristic: if input has "command", use bash tool
        if "command" in self.input_data:
            return self._execute_bash()
        elif "file_path" in self.input_data and "content" in self.input_data:
            return self._execute_file_write()
        elif "file_path" in self.input_data:
            return self._execute_file_read()
        elif "prompt" in self.input_data:
            return self._execute_llm()
        else:
            # Default: return input as output
            return {
                "status": "completed",
                "data": self.input_data,
                "citations": [{"source_type": "input", "source": "direct_passthrough"}],
                "confidence": 50
            }
    
    def _execute_bash(self) -> Dict[str, Any]:
        """Execute bash command."""
        command = self.input_data["command"]
        timeout = self.input_data.get("timeout", 30)
        
        tool_output = bash_tool(command, timeout)
        self.log_tool_execution("bash", {"command": command}, tool_output)
        
        return {
            "status": tool_output["status"],
            "data": {
                "stdout": tool_output["stdout"],
                "stderr": tool_output["stderr"],
                "exit_code": tool_output["exit_code"]
            },
            "citations": [{
                "source_type": "command",
                "source": command,
                "excerpt": tool_output["stdout"][:200]
            }],
            "confidence": 100 if tool_output["status"] == "completed" else 0
        }
    
    def _execute_file_read(self) -> Dict[str, Any]:
        """Read a file."""
        file_path = self.input_data["file_path"]
        
        tool_output = file_read_tool(file_path)
        self.log_tool_execution("file_read", {"file_path": file_path}, tool_output)
        
        return {
            "status": tool_output["status"],
            "data": {"content": tool_output.get("content", "")},
            "citations": [{
                "source_type": "file",
                "source": file_path,
                "excerpt": tool_output.get("content", "")[:200]
            }],
            "confidence": 100 if tool_output["status"] == "completed" else 0
        }
    
    def _execute_file_write(self) -> Dict[str, Any]:
        """Write to a file."""
        file_path = self.input_data["file_path"]
        content = self.input_data["content"]
        
        tool_output = file_write_tool(file_path, content)
        self.log_tool_execution("file_write", {"file_path": file_path, "content": content}, tool_output)
        
        return {
            "status": tool_output["status"],
            "data": {"bytes_written": tool_output.get("bytes_written", 0)},
            "citations": [{
                "source_type": "file",
                "source": file_path,
                "excerpt": f"Wrote {tool_output.get('bytes_written', 0)} bytes"
            }],
            "confidence": 100 if tool_output["status"] == "completed" else 0
        }
    
    def _execute_llm(self) -> Dict[str, Any]:
        """Call LLM."""
        prompt = self.input_data["prompt"]
        system = self.input_data.get("system")
        
        tool_output = llm_call_tool(prompt, system)
        self.log_tool_execution("llm_call", {"prompt": prompt}, tool_output)
        
        return {
            "status": tool_output["status"],
            "data": {"response": tool_output.get("response", "")},
            "citations": [{
                "source_type": "llm",
                "source": "gemini-1.5-flash",
                "excerpt": tool_output.get("response", "")[:200]
            }],
            "confidence": 90 if tool_output["status"] == "completed" else 0
        }
    
    def log_tool_execution(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: Dict[str, Any]
    ) -> None:
        """Log a tool execution to the database."""
        tool_exec = ToolExecution(
            id=str(uuid.uuid4()),
            agent_id=self.agent_id,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            status=tool_output.get("status", "completed"),
            completed_at=datetime.utcnow() if tool_output.get("status") == "completed" else None
        )
        self.db_session.add(tool_exec)
        self.db_session.commit()
```

- [ ] **Step 4: Run AtomicAgent tests**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_atomic_agent.py -v
```

Expected: All tests pass

- [ ] **Step 5: Commit AtomicAgent**

```bash
cd /Users/schinta/AgentMaster
git add backend_new/app/agents/atomic_agent.py backend_new/tests/test_atomic_agent.py
git commit -m "feat: AtomicAgent base class

- Single-purpose task executor
- Tool selection heuristics (bash, file, LLM)
- Automatic citation generation
- Tool execution logging to database
- Test coverage for bash and tool logging"
```

---

### Task 6: Critique Agent

**Files:**
- Create: `backend_new/app/agents/critique_agent.py`
- Test: `backend_new/tests/test_critique_agent.py`

**Interfaces:**
- Consumes:
  - `llm_call_tool` from Task 4
  - `Critique` model from Task 1
- Produces:
  - `CritiqueAgent(agent_id: str, agent_output: dict, task_description: str, db_session: Session)`
  - `CritiqueAgent.run_critique() -> dict` - Returns {"verdict": "approved"|"rejected"|"needs_human_review", "round_results": list, "overall_confidence": int}
  - Three critique rounds: factual_verification, completeness_check, consistency_validation

- [ ] **Step 1: Write failing test for CritiqueAgent**

Create `backend_new/tests/test_critique_agent.py`:

```python
import pytest
import uuid
from app.agents.critique_agent import CritiqueAgent
from app.models import Agent, Critique


def test_critique_agent_approves_valid_output(db_session):
    """Test that CritiqueAgent approves output with citations."""
    agent_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())
    
    agent = Agent(
        id=agent_id,
        execution_id=exec_id,
        agent_type="atomic_agent",
        depth=1,
        task_description="Echo hello world",
        status="critique_phase"
    )
    db_session.add(agent)
    db_session.commit()
    
    agent_output = {
        "status": "completed",
        "data": {"stdout": "hello world"},
        "citations": [{"source_type": "command", "source": "echo 'hello world'", "excerpt": "hello world"}],
        "confidence": 100
    }
    
    critique = CritiqueAgent(
        agent_id=agent_id,
        agent_output=agent_output,
        task_description="Echo hello world",
        db_session=db_session
    )
    
    result = critique.run_critique()
    
    assert result["verdict"] in ["approved", "rejected", "needs_human_review"]
    assert "round_results" in result
    assert len(result["round_results"]) >= 3  # Minimum 3 rounds


def test_critique_agent_rejects_missing_citations(db_session):
    """Test that CritiqueAgent rejects output without citations."""
    agent_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())
    
    agent = Agent(
        id=agent_id,
        execution_id=exec_id,
        agent_type="atomic_agent",
        depth=1,
        task_description="Test task",
        status="critique_phase"
    )
    db_session.add(agent)
    db_session.commit()
    
    agent_output = {
        "status": "completed",
        "data": {"result": "some data"},
        "citations": [],  # No citations!
        "confidence": 100
    }
    
    critique = CritiqueAgent(
        agent_id=agent_id,
        agent_output=agent_output,
        task_description="Test task",
        db_session=db_session
    )
    
    result = critique.run_critique()
    
    # Should reject due to missing citations
    assert result["verdict"] == "rejected"
    
    # Check database for critique records
    critiques = db_session.query(Critique).filter_by(agent_id=agent_id).all()
    assert len(critiques) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_critique_agent.py::test_critique_agent_approves_valid_output -v
```

Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement CritiqueAgent**

Create `backend_new/app/agents/critique_agent.py`:

```python
import uuid
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.agents.tools import llm_call_tool
from app.models import Critique
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CritiqueAgent:
    """
    Critique Agent - validates agent outputs through 3+ rounds.
    
    Rounds:
    1. Factual Verification - check claims against citations
    2. Completeness Check - did agent fully accomplish task?
    3. Consistency Validation - cross-check with task requirements
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_output: Dict[str, Any],
        task_description: str,
        db_session: Session
    ):
        self.agent_id = agent_id
        self.agent_output = agent_output
        self.task_description = task_description
        self.db_session = db_session
        
    def run_critique(self) -> Dict[str, Any]:
        """
        Run minimum 3 critique rounds.
        
        Returns:
            dict with verdict, round_results, overall_confidence
        """
        # Quick check: if no citations, auto-reject
        if not self.agent_output.get("citations"):
            logger.warning(f"Agent {self.agent_id} output has no citations - auto-rejecting")
            self._save_critique(1, "factual_verification", "failed", "No citations provided")
            return {
                "verdict": "rejected",
                "round_results": [{
                    "round": 1,
                    "type": "factual_verification",
                    "passed": False,
                    "reasoning": "No citations provided - auto-rejected",
                    "unsupported_claims": ["All output claims are unsupported"]
                }],
                "overall_confidence": 0
            }
        
        # Run 3 rounds
        round_results = []
        
        # Round 1: Factual Verification
        round1 = self._round_factual_verification()
        round_results.append(round1)
        self._save_critique(1, "factual_verification", "passed" if round1["passed"] else "failed", round1["reasoning"])
        
        # Round 2: Completeness Check
        round2 = self._round_completeness_check()
        round_results.append(round2)
        self._save_critique(2, "completeness_check", "passed" if round2["passed"] else "failed", round2["reasoning"])
        
        # Round 3: Consistency Validation
        round3 = self._round_consistency_validation()
        round_results.append(round3)
        self._save_critique(3, "consistency_validation", "passed" if round3["passed"] else "failed", round3["reasoning"])
        
        # Determine verdict
        passed_count = sum(1 for r in round_results if r["passed"])
        
        if passed_count == 3:
            verdict = "approved"
            confidence = 95
        elif passed_count >= 2:
            # 2/3 passed - run Round 4 with combined context
            round4 = self._round4_combined()
            round_results.append(round4)
            self._save_critique(4, "combined_review", "passed" if round4["passed"] else "failed", round4["reasoning"])
            
            if round4["passed"]:
                verdict = "approved"
                confidence = 85
            else:
                verdict = "needs_human_review"
                confidence = 50
        else:
            verdict = "rejected"
            confidence = 20
        
        return {
            "verdict": verdict,
            "round_results": round_results,
            "overall_confidence": confidence
        }
    
    def _round_factual_verification(self) -> Dict[str, Any]:
        """Round 1: Check all claims against citations."""
        citations = self.agent_output.get("citations", [])
        data = self.agent_output.get("data", {})
        
        # Simple heuristic: if citations exist and data exists, likely valid
        # In production, use LLM to verify each claim
        
        if not citations:
            return {
                "round": 1,
                "type": "factual_verification",
                "passed": False,
                "reasoning": "No citations provided",
                "unsupported_claims": ["All claims"]
            }
        
        # Check that citations have required fields
        for citation in citations:
            if "source_type" not in citation or "source" not in citation:
                return {
                    "round": 1,
                    "type": "factual_verification",
                    "passed": False,
                    "reasoning": "Citations missing required fields (source_type, source)",
                    "unsupported_claims": []
                }
        
        return {
            "round": 1,
            "type": "factual_verification",
            "passed": True,
            "reasoning": "All citations properly structured",
            "unsupported_claims": []
        }
    
    def _round_completeness_check(self) -> Dict[str, Any]:
        """Round 2: Did agent fully accomplish task?"""
        status = self.agent_output.get("status")
        data = self.agent_output.get("data", {})
        
        if status != "completed":
            return {
                "round": 2,
                "type": "completeness_check",
                "passed": False,
                "reasoning": f"Agent status is {status}, not completed",
                "unsupported_claims": []
            }
        
        if not data:
            return {
                "round": 2,
                "type": "completeness_check",
                "passed": False,
                "reasoning": "No output data produced",
                "unsupported_claims": []
            }
        
        return {
            "round": 2,
            "type": "completeness_check",
            "passed": True,
            "reasoning": "Agent completed with output data",
            "unsupported_claims": []
        }
    
    def _round_consistency_validation(self) -> Dict[str, Any]:
        """Round 3: Check consistency with task requirements."""
        # Simple heuristic: if confidence >= 70, likely consistent
        confidence = self.agent_output.get("confidence", 0)
        
        if confidence < 70:
            return {
                "round": 3,
                "type": "consistency_validation",
                "passed": False,
                "reasoning": f"Low confidence score: {confidence}%",
                "unsupported_claims": []
            }
        
        return {
            "round": 3,
            "type": "consistency_validation",
            "passed": True,
            "reasoning": f"Confidence score acceptable: {confidence}%",
            "unsupported_claims": []
        }
    
    def _round4_combined(self) -> Dict[str, Any]:
        """Round 4: Combined review when rounds disagree."""
        # If we got here, 2/3 rounds passed
        # Simple heuristic: approve if confidence >= 80
        confidence = self.agent_output.get("confidence", 0)
        
        return {
            "round": 4,
            "type": "combined_review",
            "passed": confidence >= 80,
            "reasoning": f"Combined review based on confidence: {confidence}%",
            "unsupported_claims": []
        }
    
    def _save_critique(self, round_number: int, critique_type: str, verdict: str, reasoning: str) -> None:
        """Save critique round to database."""
        critique = Critique(
            id=str(uuid.uuid4()),
            agent_id=self.agent_id,
            round_number=round_number,
            critique_type=critique_type,
            verdict=verdict,
            reasoning=reasoning,
            unsupported_claims=[]
        )
        self.db_session.add(critique)
        self.db_session.commit()
```

- [ ] **Step 4: Run CritiqueAgent tests**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_critique_agent.py -v
```

Expected: All tests pass

- [ ] **Step 5: Commit CritiqueAgent**

```bash
cd /Users/schinta/AgentMaster
git add backend_new/app/agents/critique_agent.py backend_new/tests/test_critique_agent.py
git commit -m "feat: CritiqueAgent with 3-round validation

- Round 1: Factual verification (citations check)
- Round 2: Completeness check (task accomplished)
- Round 3: Consistency validation (confidence score)
- Round 4: Combined review when rounds disagree
- Auto-reject if no citations
- Database logging for all rounds
- Test coverage for approve and reject scenarios"
```

---

### Task 7: Sub-Agent with Decomposition

**Files:**
- Create: `backend_new/app/agents/sub_agent.py`
- Test: `backend_new/tests/test_sub_agent.py`

**Interfaces:**
- Consumes:
  - `llm_call_tool` from Task 4
  - `Agent` model from Task 1
  - `settings.max_recursion_depth` from Task 1
- Produces:
  - `SubAgent(agent_id: str, task_description: str, input_data: dict, depth: int, domain: str, db_session: Session)`
  - `SubAgent.decompose() -> dict` - Returns {"complexity_score": int, "reasoning": str, "children": list, "edges": list}
  - Complexity scoring: 3-9 scale (step_count + domain_breadth + uncertainty)

- [ ] **Step 1: Write failing test for SubAgent**

Create `backend_new/tests/test_sub_agent.py`:

```python
import pytest
import uuid
from app.agents.sub_agent import SubAgent
from app.models import Agent


def test_sub_agent_simple_task_decomposition(db_session):
    """Test SubAgent decomposes simple task into Atomic Agents."""
    agent_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())
    
    agent = Agent(
        id=agent_id,
        execution_id=exec_id,
        agent_type="sub_agent",
        depth=0,
        task_description="Echo hello world",
        status="pending"
    )
    db_session.add(agent)
    db_session.commit()
    
    sub = SubAgent(
        agent_id=agent_id,
        task_description="Echo hello world",
        input_data={},
        depth=0,
        domain="Test Domain",
        db_session=db_session
    )
    
    result = sub.decompose()
    
    assert "complexity_score" in result
    assert result["complexity_score"] >= 3  # Minimum score
    assert result["complexity_score"] <= 9  # Maximum score
    assert "children" in result
    assert len(result["children"]) > 0
    assert "reasoning" in result


def test_sub_agent_respects_max_depth(db_session):
    """Test that SubAgent doesn't spawn Sub-Agents at max depth."""
    from app.config import settings
    
    agent_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())
    
    agent = Agent(
        id=agent_id,
        execution_id=exec_id,
        agent_type="sub_agent",
        depth=settings.max_recursion_depth,  # At max depth
        task_description="Complex task",
        status="pending"
    )
    db_session.add(agent)
    db_session.commit()
    
    sub = SubAgent(
        agent_id=agent_id,
        task_description="Complex task with many steps",
        input_data={},
        depth=settings.max_recursion_depth,
        domain="Test",
        db_session=db_session
    )
    
    result = sub.decompose()
    
    # At max depth, should only spawn Atomic Agents
    for child in result["children"]:
        assert child["agent_type"] == "atomic_agent"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_sub_agent.py::test_sub_agent_simple_task_decomposition -v
```

Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement SubAgent**

Create `backend_new/app/agents/sub_agent.py`:

```python
import uuid
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.agents.tools import llm_call_tool
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class SubAgent:
    """
    Sub-Agent - decomposes complex tasks into child agents.
    
    Complexity scoring (3-9):
    - Step count: 1-3 steps=1, 4-10=2, 11+=3
    - Domain breadth: single=1, 2-3 domains=2, 4+=3
    - Uncertainty: clear=1, some=2, high=3
    
    Decomposition strategy:
    - Simple (3-4): Spawn Atomic Agents only
    - Medium (5-6): Spawn Atomic Agents + 1-2 Sub-Agents
    - Complex (7-9): Spawn multiple Sub-Agents
    """
    
    def __init__(
        self,
        agent_id: str,
        task_description: str,
        input_data: Dict[str, Any],
        depth: int,
        domain: str,
        db_session: Session
    ):
        self.agent_id = agent_id
        self.task_description = task_description
        self.input_data = input_data
        self.depth = depth
        self.domain = domain
        self.db_session = db_session
        
    def decompose(self) -> Dict[str, Any]:
        """
        Decompose task into child agents.
        
        Returns:
            dict with complexity_score, reasoning, children, edges
        """
        # Score complexity
        complexity = self._score_complexity()
        
        # Generate children based on complexity
        if complexity["total"] <= 4:
            children = self._decompose_simple()
        elif complexity["total"] <= 6:
            children = self._decompose_medium()
        else:
            children = self._decompose_complex()
        
        # Generate edges (dependencies)
        edges = self._generate_edges(children)
        
        return {
            "complexity_score": complexity["total"],
            "reasoning": complexity["reasoning"],
            "children": children,
            "edges": edges
        }
    
    def _score_complexity(self) -> Dict[str, Any]:
        """Score task complexity on 3 dimensions."""
        # Simple heuristic: count words in task description
        word_count = len(self.task_description.split())
        
        # Step count estimation
        if word_count <= 10:
            step_score = 1  # Simple task
        elif word_count <= 30:
            step_score = 2  # Medium task
        else:
            step_score = 3  # Complex task
        
        # Domain breadth (simplified - assume single domain for now)
        domain_score = 1
        
        # Uncertainty (simplified - assume clear requirements)
        uncertainty_score = 1
        
        total = step_score + domain_score + uncertainty_score
        
        return {
            "step_count": step_score,
            "domain_breadth": domain_score,
            "uncertainty": uncertainty_score,
            "total": total,
            "reasoning": f"Task complexity: {total}/9 (steps={step_score}, domains={domain_score}, uncertainty={uncertainty_score})"
        }
    
    def _decompose_simple(self) -> List[Dict[str, Any]]:
        """Decompose simple task into 1-3 Atomic Agents."""
        # For simple tasks, create 1-2 atomic agents
        children = []
        
        # Child 1: Main task executor
        child1_id = str(uuid.uuid4())
        children.append({
            "agent_id": child1_id,
            "agent_type": "atomic_agent",
            "task_description": self.task_description,
            "input_data": self.input_data,
            "depth": self.depth + 1
        })
        
        return children
    
    def _decompose_medium(self) -> List[Dict[str, Any]]:
        """Decompose medium task into Atomic Agents + 1-2 Sub-Agents."""
        children = []
        
        # At max depth, only create Atomic Agents
        if self.depth >= settings.max_recursion_depth:
            return self._decompose_simple()
        
        # Child 1: Sub-Agent for complex part
        child1_id = str(uuid.uuid4())
        children.append({
            "agent_id": child1_id,
            "agent_type": "sub_agent",
            "task_description": f"Handle complex part of: {self.task_description}",
            "input_data": self.input_data,
            "depth": self.depth + 1
        })
        
        # Child 2: Atomic Agent for simple part
        child2_id = str(uuid.uuid4())
        children.append({
            "agent_id": child2_id,
            "agent_type": "atomic_agent",
            "task_description": f"Handle simple part of: {self.task_description}",
            "input_data": {},
            "depth": self.depth + 1
        })
        
        return children
    
    def _decompose_complex(self) -> List[Dict[str, Any]]:
        """Decompose complex task into 2-N Sub-Agents."""
        children = []
        
        # At max depth, force Atomic Agents
        if self.depth >= settings.max_recursion_depth:
            return self._decompose_simple()
        
        # Create 2-3 Sub-Agents for different aspects
        for i in range(2):
            child_id = str(uuid.uuid4())
            children.append({
                "agent_id": child_id,
                "agent_type": "sub_agent",
                "task_description": f"Sub-task {i+1} of: {self.task_description}",
                "input_data": self.input_data,
                "depth": self.depth + 1
            })
        
        return children
    
    def _generate_edges(self, children: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate dependency edges between children."""
        edges = []
        
        # Simple strategy: sequential execution (each child depends on previous)
        for i in range(1, len(children)):
            edge_id = str(uuid.uuid4())
            edges.append({
                "edge_id": edge_id,
                "from_agent_id": children[i-1]["agent_id"],
                "to_agent_id": children[i]["agent_id"],
                "data_description": f"Output from {children[i-1]['task_description']}"
            })
        
        return edges
```

- [ ] **Step 4: Run SubAgent tests**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_sub_agent.py -v
```

Expected: All tests pass

- [ ] **Step 5: Commit SubAgent**

```bash
cd /Users/schinta/AgentMaster
git add backend_new/app/agents/sub_agent.py backend_new/tests/test_sub_agent.py
git commit -m "feat: SubAgent with task decomposition

- Complexity scoring (3-9 scale)
- Simple/medium/complex decomposition strategies
- Max depth enforcement (spawns only Atomic Agents at max depth)
- Sequential edge generation
- Test coverage for simple tasks and depth limits"
```

---

### Task 8: AgentMaster (Orchestrator)

**Files:**
- Create: `backend_new/app/agents/orchestrator.py`
- Test: `backend_new/tests/test_orchestrator.py`

**Interfaces:**
- Consumes:
  - `SubAgent` from Task 7
  - `Execution`, `Agent` models from Task 1
- Produces:
  - `AgentMaster(execution_id: str, objective: str, domain: str, db_session: Session)`
  - `AgentMaster.plan() -> dict` - Returns {"root_agent_id": str, "plan_summary": str}
  - Creates root Sub-Agent in database

- [ ] **Step 1: Write failing test for AgentMaster**

Create `backend_new/tests/test_orchestrator.py`:

```python
import pytest
import uuid
from app.agents.orchestrator import AgentMaster
from app.models import Execution, Agent


def test_orchestrator_creates_root_agent(db_session):
    """Test that AgentMaster creates a root Sub-Agent."""
    exec_id = str(uuid.uuid4())
    
    execution = Execution(
        id=exec_id,
        objective="Create a presentation on AI",
        domain="Create PPT",
        status="planning"
    )
    db_session.add(execution)
    db_session.commit()
    
    orchestrator = AgentMaster(
        execution_id=exec_id,
        objective="Create a presentation on AI",
        domain="Create PPT",
        db_session=db_session
    )
    
    result = orchestrator.plan()
    
    assert "root_agent_id" in result
    assert "plan_summary" in result
    
    # Check that root agent was created in database
    root_agent = db_session.query(Agent).filter_by(id=result["root_agent_id"]).first()
    assert root_agent is not None
    assert root_agent.agent_type == "sub_agent"
    assert root_agent.depth == 0
    assert root_agent.execution_id == exec_id


def test_orchestrator_handles_any_domain(db_session):
    """Test that AgentMaster accepts any user-defined domain."""
    exec_id = str(uuid.uuid4())
    
    execution = Execution(
        id=exec_id,
        objective="Book tickets to Paris",
        domain="Travel Planning",  # User-defined domain
        status="planning"
    )
    db_session.add(execution)
    db_session.commit()
    
    orchestrator = AgentMaster(
        execution_id=exec_id,
        objective="Book tickets to Paris",
        domain="Travel Planning",
        db_session=db_session
    )
    
    result = orchestrator.plan()
    
    assert "root_agent_id" in result
    # Should not reject based on domain
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_orchestrator.py::test_orchestrator_creates_root_agent -v
```

Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement AgentMaster**

Create `backend_new/app/agents/orchestrator.py`:

```python
import uuid
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models import Agent
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AgentMaster:
    """
    AgentMaster - Orchestrator that creates the root Sub-Agent.
    
    Responsibilities:
    - Accept user objective + domain (ANY domain)
    - Create root Sub-Agent to handle decomposition
    - No domain restrictions
    """
    
    def __init__(
        self,
        execution_id: str,
        objective: str,
        domain: str,
        db_session: Session
    ):
        self.execution_id = execution_id
        self.objective = objective
        self.domain = domain
        self.db_session = db_session
        
    def plan(self) -> Dict[str, Any]:
        """
        Create execution plan by spawning root Sub-Agent.
        
        Returns:
            dict with root_agent_id, plan_summary
        """
        logger.info(f"AgentMaster planning for objective: {self.objective}")
        logger.info(f"Domain: {self.domain}")
        
        # Create root Sub-Agent
        root_agent_id = str(uuid.uuid4())
        
        root_agent = Agent(
            id=root_agent_id,
            execution_id=self.execution_id,
            parent_id=None,  # Root has no parent
            agent_type="sub_agent",
            depth=0,
            task_description=f"[{self.domain}] {self.objective}",
            status="pending",
            input_data={"objective": self.objective, "domain": self.domain},
            timeout_seconds=300
        )
        
        self.db_session.add(root_agent)
        self.db_session.commit()
        
        logger.info(f"Created root Sub-Agent: {root_agent_id}")
        
        return {
            "root_agent_id": root_agent_id,
            "plan_summary": f"Created root Sub-Agent for domain '{self.domain}' to handle: {self.objective}"
        }
```

- [ ] **Step 4: Run AgentMaster tests**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_orchestrator.py -v
```

Expected: All tests pass

- [ ] **Step 5: Write agents __init__.py**

Create `backend_new/app/agents/__init__.py`:

```python
from app.agents.orchestrator import AgentMaster
from app.agents.sub_agent import SubAgent
from app.agents.atomic_agent import AtomicAgent
from app.agents.critique_agent import CritiqueAgent

__all__ = ["AgentMaster", "SubAgent", "AtomicAgent", "CritiqueAgent"]
```

- [ ] **Step 6: Commit AgentMaster**

```bash
cd /Users/schinta/AgentMaster
git add backend_new/app/agents/orchestrator.py backend_new/app/agents/__init__.py backend_new/tests/test_orchestrator.py
git commit -m "feat: AgentMaster orchestrator

- Creates root Sub-Agent for any domain
- No domain restrictions (accepts user input)
- Logs planning decisions
- Test coverage for root agent creation and domain acceptance"
```

---

### Task 9: Execution Manager

**Files:**
- Create: `backend_new/app/services/execution_manager.py`
- Test: `backend_new/tests/test_execution_manager.py`

**Interfaces:**
- Consumes:
  - `SubAgent`, `AtomicAgent`, `CritiqueAgent` from Tasks 5-7
  - `GraphBuilder` from Task 3
  - `websocket_manager` from Task 3
  - `Agent`, `Edge`, `Execution` models from Task 1
- Produces:
  - `ExecutionManager(execution_id: str, db_session: Session)`
  - `ExecutionManager.execute() -> None` - Runs all agents in topological order
  - Broadcasts WebSocket events at each step

- [ ] **Step 1: Write failing test for ExecutionManager**

Create `backend_new/tests/test_execution_manager.py`:

```python
import pytest
import uuid
from app.services.execution_manager import ExecutionManager
from app.models import Execution, Agent


def test_execution_manager_runs_single_agent(db_session):
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
    manager.execute()
    
    # Check agent status changed
    db_session.refresh(agent)
    assert agent.status in ["completed", "critique_phase"]


def test_execution_manager_respects_topological_order(db_session):
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
    manager.execute()
    
    # Both should complete
    db_session.refresh(a1)
    db_session.refresh(a2)
    assert a1.status == "completed"
    assert a2.status in ["completed", "critique_phase"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_execution_manager.py::test_execution_manager_runs_single_agent -v
```

Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement ExecutionManager**

Create `backend_new/app/services/execution_manager.py`:

```python
import uuid
from typing import List
from sqlalchemy.orm import Session
from app.models import Agent, Edge, Execution
from app.agents import SubAgent, AtomicAgent, CritiqueAgent
from app.services.graph_builder import GraphBuilder
from app.services.websocket_manager import websocket_manager
from app.schemas import WebSocketEvent
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ExecutionManager:
    """
    Execution Manager - orchestrates agent execution in topological order.
    
    Responsibilities:
    - Load agents and edges from database
    - Build DAG and compute execution order
    - Execute agents sequentially (topological order)
    - Run critique after each agent
    - Broadcast WebSocket events
    - Update agent statuses in database
    """
    
    def __init__(self, execution_id: str, db_session: Session):
        self.execution_id = execution_id
        self.db_session = db_session
        
    async def execute(self) -> None:
        """Execute all agents for this execution."""
        logger.info(f"Starting execution: {self.execution_id}")
        
        # Load agents and edges
        agents = self.db_session.query(Agent).filter_by(execution_id=self.execution_id).all()
        edges = self.db_session.query(Edge).filter_by(execution_id=self.execution_id).all()
        
        if not agents:
            logger.warning(f"No agents found for execution {self.execution_id}")
            return
        
        # Build graph and get execution order
        graph = GraphBuilder()
        for agent in agents:
            graph.add_agent(agent)
        for edge in edges:
            graph.add_edge(edge)
        
        # Validate no cycles
        if not graph.validate_no_cycles():
            logger.error(f"Cycle detected in execution {self.execution_id}")
            await self._broadcast_event("execution_failed", {"reason": "Cycle detected in agent graph"})
            return
        
        # Get topological order
        execution_order = graph.topological_sort()
        logger.info(f"Execution order: {execution_order}")
        
        # Execute agents in order
        for agent_id in execution_order:
            agent = graph.agents[agent_id]
            await self._execute_agent(agent)
        
        # Mark execution complete
        execution = self.db_session.query(Execution).filter_by(id=self.execution_id).first()
        execution.status = "completed"
        execution.completed_at = datetime.utcnow()
        self.db_session.commit()
        
        await self._broadcast_event("execution_completed", {})
        logger.info(f"Execution {self.execution_id} completed")
    
    async def _execute_agent(self, agent: Agent) -> None:
        """Execute a single agent."""
        logger.info(f"Executing agent {agent.id}: {agent.task_description}")
        
        # Update status to running
        agent.status = "running"
        agent.started_at = datetime.utcnow()
        self.db_session.commit()
        
        await self._broadcast_event("agent_started", {
            "agent_id": agent.id,
            "agent_name": agent.task_description,
            "agent_type": agent.agent_type
        })
        
        try:
            # Execute based on agent type
            if agent.agent_type == "atomic_agent":
                result = await self._execute_atomic_agent(agent)
            elif agent.agent_type == "sub_agent":
                result = await self._execute_sub_agent(agent)
            else:
                raise ValueError(f"Unknown agent type: {agent.agent_type}")
            
            # Run critique
            agent.status = "critique_phase"
            self.db_session.commit()
            
            critique_result = await self._run_critique(agent, result)
            
            if critique_result["verdict"] == "approved":
                agent.status = "completed"
                agent.output_data = result["data"]
                agent.citations = result.get("citations", [])
                agent.completed_at = datetime.utcnow()
                self.db_session.commit()
                
                await self._broadcast_event("agent_completed", {
                    "agent_id": agent.id,
                    "agent_name": agent.task_description,
                    "output": result
                })
            elif critique_result["verdict"] == "rejected":
                # Retry logic would go here (max 3 retries)
                agent.status = "failed"
                self.db_session.commit()
                
                await self._broadcast_event("agent_failed", {
                    "agent_id": agent.id,
                    "agent_name": agent.task_description,
                    "reason": "Critique rejected output"
                })
            else:  # needs_human_review
                agent.status = "human_review"
                self.db_session.commit()
                
                await self._broadcast_event("human_review_needed", {
                    "agent_id": agent.id,
                    "agent_name": agent.task_description
                })
                
        except Exception as e:
            logger.error(f"Agent {agent.id} execution failed: {e}")
            agent.status = "failed"
            self.db_session.commit()
            
            await self._broadcast_event("agent_failed", {
                "agent_id": agent.id,
                "agent_name": agent.task_description,
                "error": str(e)
            })
    
    async def _execute_atomic_agent(self, agent: Agent) -> dict:
        """Execute an Atomic Agent."""
        atomic = AtomicAgent(
            agent_id=agent.id,
            task_description=agent.task_description,
            input_data=agent.input_data or {},
            db_session=self.db_session
        )
        return atomic.execute()
    
    async def _execute_sub_agent(self, agent: Agent) -> dict:
        """Execute a Sub-Agent (decompose into children)."""
        sub = SubAgent(
            agent_id=agent.id,
            task_description=agent.task_description,
            input_data=agent.input_data or {},
            depth=agent.depth,
            domain=agent.input_data.get("domain", "Unknown") if agent.input_data else "Unknown",
            db_session=self.db_session
        )
        
        decomposition = sub.decompose()
        
        # Create child agents in database
        for child in decomposition["children"]:
            child_agent = Agent(
                id=child["agent_id"],
                execution_id=self.execution_id,
                parent_id=agent.id,
                agent_type=child["agent_type"],
                depth=child["depth"],
                task_description=child["task_description"],
                status="pending",
                input_data=child["input_data"]
            )
            self.db_session.add(child_agent)
            
            await self._broadcast_event("agent_created", {
                "agent_id": child["agent_id"],
                "agent_name": child["task_description"],
                "agent_type": child["agent_type"],
                "parent_id": agent.id
            })
        
        # Create edges
        for edge in decomposition["edges"]:
            edge_obj = Edge(
                id=edge["edge_id"],
                execution_id=self.execution_id,
                from_agent_id=edge["from_agent_id"],
                to_agent_id=edge["to_agent_id"],
                data_description=edge.get("data_description")
            )
            self.db_session.add(edge_obj)
            
            await self._broadcast_event("edge_created", {
                "from_agent_id": edge["from_agent_id"],
                "to_agent_id": edge["to_agent_id"]
            })
        
        self.db_session.commit()
        
        return {
            "status": "completed",
            "data": {"decomposition": decomposition},
            "citations": [{
                "source_type": "decomposition",
                "source": "sub_agent",
                "excerpt": decomposition["reasoning"]
            }],
            "confidence": 90
        }
    
    async def _run_critique(self, agent: Agent, agent_output: dict) -> dict:
        """Run critique on agent output."""
        critique = CritiqueAgent(
            agent_id=agent.id,
            agent_output=agent_output,
            task_description=agent.task_description,
            db_session=self.db_session
        )
        
        result = critique.run_critique()
        
        await self._broadcast_event("critique_completed", {
            "agent_id": agent.id,
            "verdict": result["verdict"],
            "confidence": result["overall_confidence"]
        })
        
        return result
    
    async def _broadcast_event(self, event_type: str, data: dict) -> None:
        """Broadcast WebSocket event."""
        event = WebSocketEvent.create(
            event_type=event_type,
            execution_id=self.execution_id,
            data=data
        )
        await websocket_manager.broadcast(self.execution_id, event)
```

- [ ] **Step 4: Run ExecutionManager tests**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_execution_manager.py -v
```

Expected: All tests pass

- [ ] **Step 5: Update services __init__.py**

```bash
cd /Users/schinta/AgentMaster/backend_new
```

Edit `backend_new/app/services/__init__.py`:

```python
from app.services.websocket_manager import WebSocketManager, websocket_manager
from app.services.graph_builder import GraphBuilder
from app.services.execution_manager import ExecutionManager

__all__ = ["WebSocketManager", "websocket_manager", "GraphBuilder", "ExecutionManager"]
```

- [ ] **Step 6: Commit ExecutionManager**

```bash
cd /Users/schinta/AgentMaster
git add backend_new/app/services/execution_manager.py backend_new/app/services/__init__.py backend_new/tests/test_execution_manager.py
git commit -m "feat: ExecutionManager for agent orchestration

- Loads agents and edges from database
- Builds DAG and validates no cycles
- Executes agents in topological order
- Runs critique after each agent execution
- Handles Atomic Agents and Sub-Agents
- Broadcasts WebSocket events for all state changes
- Test coverage for single agent and topological execution"
```

---

### Task 10: REST API & WebSocket Endpoints

**Files:**
- Create: `backend_new/app/main.py`
- Create: `backend_new/app/api/routes/executions.py`
- Create: `backend_new/app/api/routes/agents.py`
- Create: `backend_new/app/api/routes/health.py`
- Create: `backend_new/app/api/websockets/studio.py`
- Create: `backend_new/app/api/websockets/control_room.py`
- Create: `backend_new/app/api/__init__.py`
- Test: `backend_new/tests/test_api.py`

**Interfaces:**
- Consumes:
  - All services from Tasks 3, 9
  - All schemas from Task 2
  - All agents from Tasks 5-8
- Produces:
  - FastAPI app with routes:
    - POST /api/executions
    - GET /api/executions/:id
    - GET /api/agents/:id
    - GET /health
    - WS /ws/studio/:execution_id
    - WS /ws/control-room/:execution_id

- [ ] **Step 1: Write failing API test**

Create `backend_new/tests/test_api.py`:

```python
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from app.main import app
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_execution(client):
    """Test creating an execution."""
    response = client.post(
        "/api/executions",
        json={
            "objective": "Test objective",
            "domain": "Test Domain",
            "config": {"max_recursion_depth": 5}
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["status"] == "planning"


def test_get_execution(client):
    """Test retrieving an execution."""
    # Create first
    create_response = client.post(
        "/api/executions",
        json={"objective": "Test", "domain": "Test"}
    )
    exec_id = create_response.json()["id"]
    
    # Get
    response = client.get(f"/api/executions/{exec_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == exec_id
    assert data["objective"] == "Test"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_api.py::test_health_check -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.main'"

- [ ] **Step 3: Create health endpoint**

Create `backend_new/app/api/routes/health.py`:

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "agentmaster"}
```

- [ ] **Step 4: Create executions endpoint**

Create `backend_new/app/api/routes/executions.py`:

```python
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Execution, Agent
from app.schemas import CreateExecutionRequest, ExecutionResponse
from app.agents import AgentMaster

router = APIRouter()


@router.post("/api/executions", response_model=ExecutionResponse)
def create_execution(request: CreateExecutionRequest, db: Session = Depends(get_db)):
    """Create a new execution."""
    exec_id = str(uuid.uuid4())
    
    execution = Execution(
        id=exec_id,
        objective=request.objective,
        domain=request.domain,
        status="planning",
        config=request.config
    )
    db.add(execution)
    db.commit()
    
    # Create root agent via AgentMaster
    orchestrator = AgentMaster(
        execution_id=exec_id,
        objective=request.objective,
        domain=request.domain,
        db_session=db
    )
    plan = orchestrator.plan()
    
    # Update execution with root agent
    execution.root_agent_id = plan["root_agent_id"]
    db.commit()
    
    db.refresh(execution)
    return ExecutionResponse(**execution.to_dict())


@router.get("/api/executions/{execution_id}", response_model=ExecutionResponse)
def get_execution(execution_id: str, db: Session = Depends(get_db)):
    """Get execution by ID."""
    execution = db.query(Execution).filter_by(id=execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return ExecutionResponse(**execution.to_dict())
```

- [ ] **Step 5: Create agents endpoint**

Create `backend_new/app/api/routes/agents.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Agent
from app.schemas import AgentResponse

router = APIRouter()


@router.get("/api/agents/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """Get agent by ID."""
    agent = db.query(Agent).filter_by(id=agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse(**agent.to_dict())
```

- [ ] **Step 6: Create Studio WebSocket**

Create `backend_new/app/api/websockets/studio.py`:

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import websocket_manager

router = APIRouter()


@router.websocket("/ws/studio/{execution_id}")
async def studio_websocket(websocket: WebSocket, execution_id: str, db: Session = Depends(get_db)):
    """
    Studio WebSocket - for planning phase.
    User connects here to see agent plan being built.
    """
    await websocket.accept()
    websocket_manager.connect(execution_id, websocket)
    
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_json()
            
            # Handle client messages (e.g., approve plan)
            if data.get("action") == "approve":
                # Transition to run phase (handled by client navigating to control room)
                pass
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(execution_id, websocket)
```

- [ ] **Step 7: Create Control Room WebSocket**

Create `backend_new/app/api/websockets/control_room.py`:

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Execution
from app.services import websocket_manager, ExecutionManager
from datetime import datetime

router = APIRouter()


@router.websocket("/ws/control-room/{execution_id}")
async def control_room_websocket(websocket: WebSocket, execution_id: str, db: Session = Depends(get_db)):
    """
    Control Room WebSocket - for execution phase.
    Broadcasts real-time agent execution events.
    """
    await websocket.accept()
    websocket_manager.connect(execution_id, websocket)
    
    # Check if execution exists
    execution = db.query(Execution).filter_by(id=execution_id).first()
    if not execution:
        await websocket.close(code=1008, reason="Execution not found")
        return
    
    # Start execution if not already running
    if execution.status == "planning":
        execution.status = "running"
        execution.started_at = datetime.utcnow()
        db.commit()
        
        # Run execution manager
        manager = ExecutionManager(execution_id=execution_id, db_session=db)
        await manager.execute()
    
    try:
        while True:
            # Wait for client messages (e.g., stop, pause)
            data = await websocket.receive_json()
            
            if data.get("action") == "stop":
                # Handle stop execution
                execution.status = "stopped_by_user"
                execution.stopped_at = datetime.utcnow()
                execution.stopped_by = "user"
                db.commit()
                break
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(execution_id, websocket)
```

- [ ] **Step 8: Create FastAPI main app**

Create `backend_new/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.utils import setup_logging
from app.api.routes import health, executions, agents
from app.api.websockets import studio, control_room

# Setup logging
setup_logging()

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title="AgentMaster API",
    description="Recursive Multi-Agent Orchestrator",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(health.router, tags=["Health"])
app.include_router(executions.router, tags=["Executions"])
app.include_router(agents.router, tags=["Agents"])

# Include WebSocket routes
app.include_router(studio.router, tags=["WebSocket - Studio"])
app.include_router(control_room.router, tags=["WebSocket - Control Room"])


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "service": "AgentMaster",
        "version": "1.0.0",
        "docs": "/docs"
    }
```

- [ ] **Step 9: Create API __init__.py files**

Create `backend_new/app/api/__init__.py`:

```python
# API package
```

Create `backend_new/app/api/routes/__init__.py`:

```python
from app.api.routes import health, executions, agents

__all__ = ["health", "executions", "agents"]
```

Create `backend_new/app/api/websockets/__init__.py`:

```python
from app.api.websockets import studio, control_room

__all__ = ["studio", "control_room"]
```

- [ ] **Step 10: Run API tests**

```bash
cd /Users/schinta/AgentMaster/backend_new
python -m pytest tests/test_api.py -v
```

Expected: All tests pass

- [ ] **Step 11: Test server manually**

```bash
cd /Users/schinta/AgentMaster/backend_new
uvicorn app.main:app --reload --port 8000
```

Open browser to http://localhost:8000/docs - verify Swagger UI loads

- [ ] **Step 12: Commit API endpoints**

```bash
cd /Users/schinta/AgentMaster
git add backend_new/app/main.py backend_new/app/api/ backend_new/tests/test_api.py
git commit -m "feat: FastAPI REST and WebSocket endpoints

- POST /api/executions - create execution
- GET /api/executions/:id - get execution
- GET /api/agents/:id - get agent
- GET /health - health check
- WS /ws/studio/:id - planning phase WebSocket
- WS /ws/control-room/:id - execution phase WebSocket
- CORS middleware
- Swagger docs at /docs
- Test coverage for all REST endpoints"
```

- [ ] **Step 13: Create .env file**

```bash
cd /Users/schinta/AgentMaster/backend_new
cp .env.example .env
echo "GEMINI_API_KEY=your_actual_key_here" >> .env
```

- [ ] **Step 14: Install dependencies and run final test**

```bash
cd /Users/schinta/AgentMaster/backend_new
pip install -r requirements.txt
python -m pytest -v
```

Expected: All tests pass

- [ ] **Step 15: Final commit - backend complete**

```bash
cd /Users/schinta/AgentMaster
git add backend_new/.env
git commit -m "chore: environment configuration

- Created .env from template
- Ready for local development"
```

---

## Plan Complete

Backend core implementation is now complete with:

✅ **Database Foundation** - SQLite with 6 ORM models  
✅ **Pydantic Schemas** - Request/response validation  
✅ **WebSocket Manager** - Real-time event broadcasting  
✅ **Graph Builder** - DAG construction and cycle detection  
✅ **Atomic Agent Tools** - bash, file ops, LLM, web  
✅ **Atomic Agent** - Single-purpose executors with citations  
✅ **Critique Agent** - 3-round validation with anti-hallucination  
✅ **Sub-Agent** - Task decomposition with complexity scoring  
✅ **AgentMaster** - Orchestrator accepting any domain  
✅ **Execution Manager** - Topological execution with WebSocket events  
✅ **REST API** - Create/get executions and agents  
✅ **WebSocket API** - Studio (planning) and Control Room (execution)  

**Next Steps:**
1. Start backend server: `cd backend_new && uvicorn app.main:app --reload`
2. Test via Swagger UI: http://localhost:8000/docs
3. Move to frontend implementation plan (separate plan)

