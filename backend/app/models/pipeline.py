from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, JSON, DateTime
from sqlalchemy.sql import func
from app.db import Base


class InputField(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True


class Pipeline(BaseModel):
    id: str
    objective: str
    name: str
    input_schema: list[InputField] = Field(default_factory=list)
    blueprint: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class PipelineSummary(BaseModel):
    id: str
    objective: str
    name: str
    agent_count: int = 0
    created_at: str | None = None


class PipelineORM(Base):
    __tablename__ = "pipelines"

    id = Column(String, primary_key=True)
    objective = Column(String, nullable=False)
    name = Column(String, nullable=False)
    input_schema = Column(JSON, default=list)
    blueprint = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
