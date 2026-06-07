import logging
from app.models.dag import DAGGraph, DAGNode, DAGEdge

logger = logging.getLogger(__name__)


class DAGEngine:
    def __init__(self, graph: DAGGraph):
        self.graph = graph
        self._mutation_log: list[dict] = []

    def get_ready_nodes(self, completed: set[str]) -> list[DAGNode]:
        return self.graph.get_ready_nodes(completed)

    def inject_node(
        self,
        node: DAGNode,
        after_node_id: str | None = None,
        reason: str = "",
    ) -> None:
        self.graph.add_node(node)
        if after_node_id and after_node_id in self.graph.nodes:
            edge = DAGEdge(
                edge_id=f"e_{after_node_id}_{node.node_id}",
                from_node=after_node_id,
                to_node=node.node_id,
            )
            self.graph.add_edge(edge)
        self._mutation_log.append(
            {"action": "inject_node", "node_id": node.node_id, "after": after_node_id, "reason": reason}
        )
        logger.info("DAG mutation: injected node %s after %s. Reason: %s", node.node_id, after_node_id, reason)

    def inject_edge(self, edge: DAGEdge, reason: str = "") -> None:
        self.graph.add_edge(edge)
        self._mutation_log.append({"action": "inject_edge", "edge_id": edge.edge_id, "reason": reason})

    def get_mutation_log(self) -> list[dict]:
        return list(self._mutation_log)

    def is_complete(self, completed: set[str]) -> bool:
        return len(completed) == len(self.graph.nodes)
