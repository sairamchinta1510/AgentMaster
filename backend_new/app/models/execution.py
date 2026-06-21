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
