import uuid
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.agents.tools import llm_call_tool
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class SubAgent:
    """
    Sub-Agent - decomposes complex tasks into child agents.

    Complexity scoring (3-9):
    - Step count: 1-3 steps=1, 4-10=2, 11+=3
    - Domain breadth: single=1, 2-3 domains=2, 4+=3
    - Uncertainty: clear=1, some=2, high=3

    Decomposition strategy:
    - Simple (3-4): Spawn Atomic Agents only
    - Medium (5-6): Spawn Atomic Agents + 1-2 Sub-Agents
    - Complex (7-9): Spawn multiple Sub-Agents
    """

    def __init__(
        self,
        agent_id: str,
        task_description: str,
        input_data: Dict[str, Any],
        depth: int,
        domain: str,
        db_session: Session
    ):
        self.agent_id = agent_id
        self.task_description = task_description
        self.input_data = input_data
        self.depth = depth
        self.domain = domain
        self.db_session = db_session

    def decompose(self) -> Dict[str, Any]:
        """
        Decompose task into child agents.

        Returns:
            dict with complexity_score, reasoning, children, edges
        """
        # Score complexity
        complexity = self._score_complexity()

        # Generate children based on complexity
        if complexity["total"] <= 4:
            children = self._decompose_simple()
        elif complexity["total"] <= 6:
            children = self._decompose_medium()
        else:
            children = self._decompose_complex()

        # Generate edges (dependencies)
        edges = self._generate_edges(children)

        return {
            "complexity_score": complexity["total"],
            "reasoning": complexity["reasoning"],
            "children": children,
            "edges": edges
        }

    def _score_complexity(self) -> Dict[str, Any]:
        """Score task complexity on 3 dimensions."""
        # Simple heuristic: count words in task description
        word_count = len(self.task_description.split())

        # Step count estimation
        if word_count <= 10:
            step_score = 1  # Simple task
        elif word_count <= 30:
            step_score = 2  # Medium task
        else:
            step_score = 3  # Complex task

        # Domain breadth (simplified - assume single domain for now)
        domain_score = 1

        # Uncertainty (simplified - assume clear requirements)
        uncertainty_score = 1

        total = step_score + domain_score + uncertainty_score

        return {
            "step_count": step_score,
            "domain_breadth": domain_score,
            "uncertainty": uncertainty_score,
            "total": total,
            "reasoning": f"Task complexity: {total}/9 (steps={step_score}, domains={domain_score}, uncertainty={uncertainty_score})"
        }

    def _decompose_simple(self) -> List[Dict[str, Any]]:
        """Decompose simple task into 1-3 Atomic Agents."""
        # For simple tasks, create 1-2 atomic agents
        children = []

        # Child 1: Main task executor
        child1_id = str(uuid.uuid4())
        children.append({
            "agent_id": child1_id,
            "agent_type": "atomic_agent",
            "task_description": self.task_description,
            "input_data": self.input_data,
            "depth": self.depth + 1
        })

        return children

    def _decompose_medium(self) -> List[Dict[str, Any]]:
        """Decompose medium task into Atomic Agents + 1-2 Sub-Agents."""
        children = []

        # At depth N-1, only create Atomic Agents (children will be at depth N, the max)
        if self.depth >= settings.max_recursion_depth - 1:
            return self._decompose_simple()

        # Child 1: Sub-Agent for complex part
        child1_id = str(uuid.uuid4())
        children.append({
            "agent_id": child1_id,
            "agent_type": "sub_agent",
            "task_description": f"Handle complex part of: {self.task_description}",
            "input_data": self.input_data,
            "depth": self.depth + 1
        })

        # Child 2: Atomic Agent for simple part
        child2_id = str(uuid.uuid4())
        children.append({
            "agent_id": child2_id,
            "agent_type": "atomic_agent",
            "task_description": f"Handle simple part of: {self.task_description}",
            "input_data": {},
            "depth": self.depth + 1
        })

        return children

    def _decompose_complex(self) -> List[Dict[str, Any]]:
        """Decompose complex task into 2-N Sub-Agents."""
        children = []

        # At depth N-1, force Atomic Agents (children will be at depth N, the max)
        if self.depth >= settings.max_recursion_depth - 1:
            return self._decompose_simple()

        # Create 2-3 Sub-Agents for different aspects
        for i in range(2):
            child_id = str(uuid.uuid4())
            children.append({
                "agent_id": child_id,
                "agent_type": "sub_agent",
                "task_description": f"Sub-task {i+1} of: {self.task_description}",
                "input_data": self.input_data,
                "depth": self.depth + 1
            })

        return children

    def _generate_edges(self, children: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate dependency edges between children."""
        edges = []

        # Simple strategy: sequential execution (each child depends on previous)
        for i in range(1, len(children)):
            edge_id = str(uuid.uuid4())
            edges.append({
                "edge_id": edge_id,
                "from_agent_id": children[i-1]["agent_id"],
                "to_agent_id": children[i]["agent_id"],
                "data_description": f"Output from {children[i-1]['task_description']}"
            })

        return edges
