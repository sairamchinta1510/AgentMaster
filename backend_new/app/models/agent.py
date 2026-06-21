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
