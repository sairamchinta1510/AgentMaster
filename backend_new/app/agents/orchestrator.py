import uuid
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models import Agent
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AgentMaster:
    """
    AgentMaster - Orchestrator that creates the root Sub-Agent.

    Responsibilities:
    - Accept user objective + domain (ANY domain)
    - Create root Sub-Agent to handle decomposition
    - No domain restrictions
    """

    def __init__(
        self,
        execution_id: str,
        objective: str,
        domain: str,
        db_session: Session
    ):
        self.execution_id = execution_id
        self.objective = objective
        self.domain = domain
        self.db_session = db_session

    def plan(self) -> Dict[str, Any]:
        """
        Create execution plan by spawning root Sub-Agent.

        Returns:
            dict with root_agent_id, plan_summary
        """
        logger.info(f"AgentMaster planning for objective: {self.objective}")
        logger.info(f"Domain: {self.domain}")

        # Create root Sub-Agent
        root_agent_id = str(uuid.uuid4())

        root_agent = Agent(
            id=root_agent_id,
            execution_id=self.execution_id,
            parent_id=None,  # Root has no parent
            agent_type="sub_agent",
            depth=0,
            task_description=f"[{self.domain}] {self.objective}",
            status="pending",
            input_data={"objective": self.objective, "domain": self.domain},
            timeout_seconds=300
        )

        self.db_session.add(root_agent)
        self.db_session.commit()

        logger.info(f"Created root Sub-Agent: {root_agent_id}")

        return {
            "root_agent_id": root_agent_id,
            "plan_summary": f"Created root Sub-Agent for domain '{self.domain}' to handle: {self.objective}"
        }
