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
