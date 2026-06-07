from pydantic import BaseModel, Field
from typing import Any
from sqlalchemy import Column, String, JSON, ForeignKey
from app.db import Base


class DAGNode(BaseModel):
    node_id: str
    agent_id: str
    agent_name: str
    depends_on: list[str] = Field(default_factory=list)


class DAGEdge(BaseModel):
    edge_id: str
    from_node: str
    to_node: str
    payload_schema: dict[str, Any] = Field(default_factory=dict)


class DAGGraph(BaseModel):
    session_id: str
    nodes: dict[str, DAGNode] = Field(default_factory=dict)
    edges: list[DAGEdge] = Field(default_factory=list)

    def add_node(self, node: DAGNode) -> None:
        self.nodes[node.node_id] = node

    def add_edge(self, edge: DAGEdge) -> None:
        self.edges.append(edge)
        if edge.to_node in self.nodes:
            target = self.nodes[edge.to_node]
            if edge.from_node not in target.depends_on:
                target.depends_on.append(edge.from_node)

    def get_ready_nodes(self, completed_node_ids: set[str]) -> list[DAGNode]:
        """Return nodes whose all dependencies are in completed_node_ids."""
        ready = []
        for node_id, node in self.nodes.items():
            if node_id in completed_node_ids:
                continue
            if all(dep in completed_node_ids for dep in node.depends_on):
                ready.append(node)
        return ready

    def topological_sort(self) -> list[str]:
        """Return node_ids in topological order (Kahn's algorithm)."""
        in_degree: dict[str, int] = {nid: 0 for nid in self.nodes}
        for edge in self.edges:
            in_degree[edge.to_node] = in_degree.get(edge.to_node, 0) + 1
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result = []
        while queue:
            node_id = queue.pop(0)
            result.append(node_id)
            for edge in self.edges:
                if edge.from_node == node_id:
                    in_degree[edge.to_node] -= 1
                    if in_degree[edge.to_node] == 0:
                        queue.append(edge.to_node)
        return result


class DAGGraphORM(Base):
    __tablename__ = "dag_graphs"

    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("execution_sessions.id"))
    graph_json = Column(JSON)
