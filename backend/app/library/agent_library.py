import uuid
import logging
from sqlalchemy import create_engine, Column, String, Float, JSON, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.sql import func
from app.models.dag import DAGGraph

logger = logging.getLogger(__name__)


class LibBase(DeclarativeBase):
    pass


class AgentPatternORM(LibBase):
    __tablename__ = "agent_patterns"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String)
    name = Column(String)
    objective = Column(Text)
    domain = Column(String)
    dag_json = Column(JSON)
    quality_score = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AgentLibrary:
    def __init__(self, db_url: str = "sqlite:///./agentmaster.db"):
        self.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        LibBase.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def save_flow(
        self,
        session_id: str,
        name: str,
        objective: str,
        domain: str,
        graph: DAGGraph,
        quality_score: float,
    ) -> str:
        with self.Session() as session:
            pattern_id = str(uuid.uuid4())
            pattern = AgentPatternORM(
                id=pattern_id,
                session_id=session_id,
                name=name,
                objective=objective,
                domain=domain,
                dag_json=graph.model_dump(),
                quality_score=quality_score,
            )
            session.add(pattern)
            session.commit()
            logger.info("Saved flow '%s' to Agent Library (id=%s)", name, pattern_id)
            return pattern_id

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Keyword search against objective and name fields."""
        with self.Session() as session:
            patterns = session.query(AgentPatternORM).all()
        query_lower = query.lower()
        query_words = query_lower.split()
        results = []
        for p in patterns:
            score = 0
            obj = (p.objective or "").lower()
            name = (p.name or "").lower()
            if query_lower in obj:
                score += 3
            if query_lower in name:
                score += 2
            for word in query_words:
                if word in obj:
                    score += 1
                if word in name:
                    score += 1
            if score > 0:
                results.append(
                    {
                        "id": p.id,
                        "name": p.name,
                        "objective": p.objective,
                        "domain": p.domain,
                        "quality_score": p.quality_score,
                        "score": score,
                    }
                )
        results.sort(key=lambda x: (-x["score"], -(x["quality_score"] or 0)))
        return results[:limit]

    def get_by_id(self, pattern_id: str) -> dict | None:
        with self.Session() as session:
            p = session.query(AgentPatternORM).filter_by(id=pattern_id).first()
            if not p:
                return None
            return {
                "id": p.id,
                "name": p.name,
                "objective": p.objective,
                "domain": p.domain,
                "dag_json": p.dag_json,
                "quality_score": p.quality_score,
                "session_id": p.session_id,
            }

    def list_all(self) -> list[dict]:
        with self.Session() as session:
            patterns = (
                session.query(AgentPatternORM)
                .order_by(AgentPatternORM.quality_score.desc())
                .all()
            )
        return [
            {
                "id": p.id,
                "name": p.name,
                "domain": p.domain,
                "quality_score": p.quality_score,
                "objective": (p.objective or "")[:100],
            }
            for p in patterns
        ]
