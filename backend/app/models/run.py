from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db import Base


class AgentResult(BaseModel):
    agent_id: str
    agent_name: str
    status: str
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    duration_ms: int | None = None


class Run(BaseModel):
    id: str
    pipeline_id: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"
    results: list[AgentResult] = Field(default_factory=list)
    created_at: str | None = None
    completed_at: str | None = None


class RunORM(Base):
    __tablename__ = "runs"

    id = Column(String, primary_key=True)
    pipeline_id = Column(String, ForeignKey("pipelines.id"), nullable=False)
    inputs = Column(JSON, default=dict)
    status = Column(String, default="pending")
    results = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    triggered_by = Column(String, default="manual")  # "manual" | "schedule" | "webhook"
