from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Critique(Base):
    __tablename__ = "critiques"

    id = Column(String, primary_key=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    round_number = Column(Integer, nullable=False, index=True)
    critique_type = Column(String, nullable=False)  # factual_verification | completeness_check | consistency_validation
    verdict = Column(String, nullable=False)  # passed | failed
    reasoning = Column(Text, nullable=False)
    unsupported_claims = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "round_number": self.round_number,
            "critique_type": self.critique_type,
            "verdict": self.verdict,
            "reasoning": self.reasoning,
            "unsupported_claims": self.unsupported_claims,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
