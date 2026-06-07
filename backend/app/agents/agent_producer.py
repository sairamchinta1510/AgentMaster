import json
import logging
from openai import AsyncOpenAI
from app.config import settings
from app.prompts.producer import get_producer_prompt
from app.models.agent import AtomicAgent

logger = logging.getLogger(__name__)


def make_llm_client() -> tuple[AsyncOpenAI, str]:
    return AsyncOpenAI(
        api_key=settings.active_api_key,
        base_url=settings.active_base_url,
    ), settings.active_model


def _normalize_user_inputs(raw: list) -> list[dict]:
    """Coerce LLM output to list[dict] — LLMs sometimes return list[str]."""
    result = []
    for item in raw:
        if isinstance(item, str):
            result.append({"name": item, "type": "string", "description": item, "required": True})
        elif isinstance(item, dict):
            result.append(item)
    return result


class AgentProducerAgent:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.client, self.model = make_llm_client()

    async def produce(
        self,
        agent_spec: dict,
        phase: str,
        session_id: str,
        user_inputs: dict | None = None,
    ) -> AtomicAgent:
        """Create a full AtomicAgent from a blueprint spec."""
        prompt = get_producer_prompt(agent_spec, phase, user_inputs or {})
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": f"Produce the complete agent specification for: {agent_spec.get('agent_name', 'Unknown')}",
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        data = json.loads(response.choices[0].message.content)
        return AtomicAgent(
            agent_id=data.get("agent_id", agent_spec.get("agent_id", "unknown")),
            agent_name=data.get("agent_name", agent_spec.get("agent_name", "Unknown")),
            session_id=session_id,
            phase=phase,
            description=data.get("description", ""),
            input_schema=data.get("input_schema", {}),
            output_schema=data.get("output_schema", {}),
            error_schema=data.get("error_schema", {}),
            required_user_inputs=_normalize_user_inputs(data.get("required_user_inputs", [])),
            timeout_seconds=data.get("timeout_seconds", 60),
            retry_policy=data.get(
                "retry_policy", {"max_retries": 3, "backoff": "exponential"}
            ),
        )

    async def revise(
        self, agent: AtomicAgent, issues: list[dict], phase: str
    ) -> AtomicAgent:
        """Revise an agent based on critique issues."""
        spec = agent.model_dump(exclude={"critique_history"})
        spec["critique_issues_to_fix"] = issues
        prompt = get_producer_prompt(spec, phase, {})
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": "Fix ALL critique issues and return the revised agent specification.",
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        data = json.loads(response.choices[0].message.content)
        agent.input_schema = data.get("input_schema", agent.input_schema)
        agent.output_schema = data.get("output_schema", agent.output_schema)
        agent.error_schema = data.get("error_schema", agent.error_schema)
        agent.description = data.get("description", agent.description)
        return agent
