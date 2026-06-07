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
    retry_policy: dict[str, Any] = Field(
        default_factory=lambda: {"max_retries": 3, "backoff": "exponential"}
    )
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
