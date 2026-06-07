from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field
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
    state: Optional[GlobalStateObject] = None

    def model_post_init(self, __context: Any) -> None:
        if self.state is None:
            self.state = GlobalStateObject(
                session_id=self.session_id,
                objective=self.objective,
            )


class ExecutionSessionORM(Base):
    __tablename__ = "execution_sessions"

    id = Column(String, primary_key=True)
    objective = Column(String)
    phase = Column(String, default="DESIGN")
    state_json = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
