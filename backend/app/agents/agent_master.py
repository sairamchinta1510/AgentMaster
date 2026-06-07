import json
import logging
from openai import AsyncOpenAI
from app.config import settings
from app.prompts.master import get_master_prompt
from app.models.dag import DAGGraph, DAGNode, DAGEdge
from app.models.session import ExecutionSession

logger = logging.getLogger(__name__)


def make_llm_client() -> tuple[AsyncOpenAI, str]:
    client = AsyncOpenAI(api_key=settings.active_api_key, base_url=settings.active_base_url)
    return client, settings.active_model


class AgentMasterAgent:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.client, self.model = make_llm_client()

    async def design_blueprint(self, session: ExecutionSession, library_context: str = "") -> dict:
        """Parse objective and return full agent blueprint as dict."""
        prompt = get_master_prompt("DESIGN", session.objective, library_context)
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": f"Design the complete agent blueprint for this objective: {session.objective}",
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = response.choices[0].message.content
        return json.loads(content)

    async def design_blueprint_raw(self, objective: str) -> dict:
        """Design blueprint from objective string directly."""
        prompt = get_master_prompt("DESIGN", objective)
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": f"Design the complete agent blueprint for this objective: {objective}",
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = response.choices[0].message.content
        return json.loads(content)

    def build_dag_from_blueprint(self, blueprint: dict, session_id: str) -> DAGGraph:
        graph = DAGGraph(session_id=session_id)
        agent_id_to_node: dict[str, str] = {}
        for agent_spec in blueprint.get("agents", []):
            node_id = f"node_{agent_spec['agent_id']}"
            node = DAGNode(
                node_id=node_id,
                agent_id=agent_spec["agent_id"],
                agent_name=agent_spec["agent_name"],
            )
            graph.add_node(node)
            agent_id_to_node[agent_spec["agent_id"]] = node_id
        for edge_spec in blueprint.get("edges", []):
            from_node = agent_id_to_node.get(edge_spec.get("from", ""))
            to_node = agent_id_to_node.get(edge_spec.get("to", ""))
            if from_node and to_node:
                edge = DAGEdge(edge_id=f"e_{from_node}_{to_node}", from_node=from_node, to_node=to_node)
                graph.add_edge(edge)
        return graph
