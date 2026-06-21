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
