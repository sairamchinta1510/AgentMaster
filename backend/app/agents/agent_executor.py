import json
import logging
import time
from typing import Any
from openai import AsyncOpenAI
from app.config import settings
from app.models.run import AgentResult

logger = logging.getLogger(__name__)


def _make_llm_client() -> tuple[AsyncOpenAI, str]:
    client = AsyncOpenAI(
        api_key=settings.active_api_key,
        base_url=settings.active_base_url,
    )
    return client, settings.active_model


EXECUTOR_SYSTEM_PROMPT = """You are an AI agent executor. Your job is to execute a single, specific agent task.

You will receive:
1. The agent's name and description (what it does)
2. Its input_schema (what fields it expects)
3. Its output_schema (what fields it should return)
4. The actual input values available

Execute the task to the best of your ability. If real tool calls / API calls are needed but not available,
simulate them realistically based on the inputs provided. Return ONLY a JSON object matching the output_schema.

Be specific and detailed in your output — don't return generic placeholders.
"""


class AgentExecutorAgent:
    def __init__(self):
        self.client, self.model = _make_llm_client()

    async def execute(
        self,
        agent_spec: dict[str, Any],
        context_inputs: dict[str, Any],
    ) -> AgentResult:
        """Execute one agent spec and return its result."""
        start_ms = int(time.time() * 1000)
        agent_id = agent_spec.get("agent_id", "unknown")
        agent_name = agent_spec.get("agent_name", "Unknown Agent")

        user_prompt = (
            f"Agent: {agent_name}\n"
            f"Description: {agent_spec.get('description', '')}\n"
            f"Input Schema: {json.dumps(agent_spec.get('input_schema', {}), indent=2)}\n"
            f"Output Schema: {json.dumps(agent_spec.get('output_schema', {}), indent=2)}\n"
            f"Available Inputs: {json.dumps(context_inputs, indent=2)}\n\n"
            "Execute this agent task and return a JSON object matching the output_schema."
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": EXECUTOR_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            output_raw = response.choices[0].message.content
            output = json.loads(output_raw)
            duration_ms = int(time.time() * 1000) - start_ms
            return AgentResult(
                agent_id=agent_id,
                agent_name=agent_name,
                status="completed",
                output=output,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            logger.error("AgentExecutor failed for %s: %s", agent_id, exc, exc_info=True)
            return AgentResult(
                agent_id=agent_id,
                agent_name=agent_name,
                status="failed",
                output={},
                error=str(exc),
                duration_ms=int(time.time() * 1000) - start_ms,
            )
