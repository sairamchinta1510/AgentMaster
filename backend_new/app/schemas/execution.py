from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class CreateExecutionRequest(BaseModel):
    objective: str = Field(..., min_length=1, description="User's goal")
    domain: str = Field(..., min_length=1, description="User-defined domain")
    config: Optional[Dict[str, Any]] = Field(default=None, description="Optional execution config")


class ExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
