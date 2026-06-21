from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict


class CitationSchema(BaseModel):
    source_type: str  # file | url | command
    source: str
    excerpt: Optional[str]


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
