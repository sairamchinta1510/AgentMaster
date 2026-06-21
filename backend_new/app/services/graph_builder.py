from typing import Dict, List, Set
from app.models import Agent, Edge
import logging

logger = logging.getLogger(__name__)


class GraphBuilder:
    """Builds and validates DAG from agents and edges."""

    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.edges: List[Edge] = []
        self.adjacency: Dict[str, List[str]] = {}  # agent_id -> [dependent_agent_ids]

    def add_agent(self, agent: Agent) -> None:
        """Add an agent to the graph."""
        self.agents[agent.id] = agent
        if agent.id not in self.adjacency:
            self.adjacency[agent.id] = []

    def add_edge(self, edge: Edge) -> None:
        """Add an edge between two agents."""
        self.edges.append(edge)

        if edge.from_agent_id not in self.adjacency:
            self.adjacency[edge.from_agent_id] = []
        if edge.to_agent_id not in self.adjacency:
            self.adjacency[edge.to_agent_id] = []

        self.adjacency[edge.from_agent_id].append(edge.to_agent_id)

    def validate_no_cycles(self) -> bool:
        """
        Validate that the graph has no cycles using DFS.
        Returns True if no cycles, False if cycle detected.
        """
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in self.adjacency.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for agent_id in self.agents:
            if agent_id not in visited:
                if has_cycle(agent_id):
                    logger.error(f"Cycle detected in graph involving agent {agent_id}")
                    return False

        return True

    def topological_sort(self) -> List[str]:
        """
        Return agents in topological order (dependency order).
        Agents with no dependencies come first.
        """
        in_degree = {agent_id: 0 for agent_id in self.agents}

        for agent_id in self.agents:
            for neighbor in self.adjacency.get(agent_id, []):
                in_degree[neighbor] += 1

        queue = [agent_id for agent_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for neighbor in self.adjacency.get(current, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self.agents):
            logger.error("Topological sort failed - graph may have cycles")
            return []

        return result
