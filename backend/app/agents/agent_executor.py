# backend/app/agents/agent_executor.py
import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from openai import AsyncOpenAI

from app.agents.code_executor import execute_python_code
from app.config import settings
from app.models.run import AgentResult

logger = logging.getLogger(__name__)


def _parse_llm_json(raw: str) -> dict:
    """Strip markdown code fences then parse JSON. Gemini often wraps output in ```json ... ```."""
    text = raw.strip()
    if text.startswith("```"):
        # Remove opening fence (```json or ```)
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        # Remove closing fence
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3].rstrip()
    return json.loads(text)


def _make_llm_client() -> tuple[AsyncOpenAI, str]:
    client = AsyncOpenAI(
        api_key=settings.active_api_key,
        base_url=settings.active_base_url,
    )
    return client, settings.active_model


PLAN_SYSTEM_PROMPT = """You are an AI agent executor. Your job is to execute a single, specific agent task.

You will receive:
1. The agent's name and description (what it does)
2. Its input_schema (what fields it expects)
3. Its output_schema (what fields it should return)
4. The actual input values available

Decide which action to take:

OPTION A — Pure reasoning (no real-world data needed, inputs contain everything):
Return ONLY this JSON:
{"action": "NO_CODE_NEEDED", "output": {<json matching output_schema>}}

OPTION B — Real-world execution required (API calls, data fetching, system queries, infrastructure changes):
Return ONLY this JSON:
{"action": "EXECUTE_CODE", "code": "<python code string>", "credential_keys": ["KEY1"]}

Code rules:
- ALL input values (paths, URLs, names, credentials) are injected as environment variables.
  The env var name is the input field name uppercased, e.g. repository_path -> os.environ["REPOSITORY_PATH"]
- List only secret/credential keys in credential_keys (informational only, all inputs are already injected)
- Print the result as a single JSON object to stdout (last print statement)
- Handle errors: print details to stderr, keep running
- Write files only to /tmp if needed — always use unique paths: use tempfile.mkdtemp() or /tmp/<uuid4> — NEVER hardcode /tmp/repo or any fixed path that could collide across runs
- NEVER run: rm -rf, kill, shutdown, or any destructive shell command
- Use only pre-installed packages: httpx, requests, boto3, google-cloud-logging,
  google-cloud-monitoring, PyGithub, kubernetes, subprocess, glob, pathlib, json, os, sys, datetime
"""

SYNTH_SYSTEM_PROMPT = """You are synthesising the result of a real code execution into a structured output.

The agent ran Python code and produced real output. Synthesise this into a JSON object
matching the output_schema exactly. Use the real data from stdout — do not fabricate.
Return ONLY a valid JSON object matching the schema.
"""


# Callback type: called when executor enters a new code phase
CodeEventCallback = Callable[[str, str, str | None], Awaitable[None]]
# Args: (agent_id, phase, code_preview)
# phase: "planning" | "executing" | "synthesising" | "fallback"


class AgentExecutorAgent:
    def __init__(self):
        self.client, self.model = _make_llm_client()

    async def execute(
        self,
        agent_spec: dict[str, Any],
        context_inputs: dict[str, Any],
        on_code_event: CodeEventCallback | None = None,
    ) -> AgentResult:
        """Execute one agent spec and return its result."""
        start_ms = int(time.time() * 1000)
        agent_id = agent_spec.get("agent_id", "unknown")
        agent_name = agent_spec.get("agent_name", "Unknown Agent")

        async def emit(phase: str, code_preview: str | None = None):
            if on_code_event:
                await on_code_event(agent_id, phase, code_preview)

        try:
            # ── PLAN phase ───────────────────────────────────────────────────
            await emit("planning")

            plan_prompt = (
                f"Agent: {agent_name}\n"
                f"Description: {agent_spec.get('description', '')}\n"
                f"Input Schema: {json.dumps(agent_spec.get('input_schema', {}), indent=2)}\n"
                f"Output Schema: {json.dumps(agent_spec.get('output_schema', {}), indent=2)}\n"
                f"Available Inputs: {json.dumps(context_inputs, indent=2)}\n\n"
                "Decide: NO_CODE_NEEDED (return output directly) or EXECUTE_CODE (write Python)."
            )

            plan_response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": PLAN_SYSTEM_PROMPT},
                    {"role": "user", "content": plan_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            plan = _parse_llm_json(plan_response.choices[0].message.content)

            # Validate plan response structure
            action = plan.get("action")
            if action not in ("NO_CODE_NEEDED", "EXECUTE_CODE"):
                raise ValueError(f"LLM returned unknown action: {action!r}. Expected NO_CODE_NEEDED or EXECUTE_CODE.")
            if action == "EXECUTE_CODE" and not plan.get("code", "").strip():
                raise ValueError("LLM returned EXECUTE_CODE but provided no code.")

            # ── FALLBACK: pure reasoning ──────────────────────────────────────
            if plan.get("action") == "NO_CODE_NEEDED":
                await emit("fallback")
                output = plan.get("output", {})
                duration_ms = int(time.time() * 1000) - start_ms
                return AgentResult(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    status="completed",
                    output=output,
                    duration_ms=duration_ms,
                )

            # ── EXEC phase ───────────────────────────────────────────────────
            code = plan.get("code", "")
            credential_keys = plan.get("credential_keys", [])
            code_preview = code[:200] if code else None
            await emit("executing", code_preview)

            # Inject ALL context inputs as uppercased env vars so generated code
            # can read any input (paths, URLs, names, credentials) via os.environ.
            # e.g. context_inputs["repository_path"] -> os.environ["REPOSITORY_PATH"]
            env_vars: dict[str, str] = {
                k.upper(): str(v)
                for k, v in context_inputs.items()
                if not k.startswith("_") and v is not None
            }

            stdout, stderr, returncode = await execute_python_code(code, env_vars)

            # ── SYNTH phase ──────────────────────────────────────────────────
            await emit("synthesising")

            synth_prompt = (
                f"Agent: {agent_name}\n"
                f"Output Schema: {json.dumps(agent_spec.get('output_schema', {}), indent=2)}\n\n"
                f"STDOUT:\n{stdout or '(empty)'}\n\n"
                f"STDERR:\n{stderr or '(none)'}\n\n"
                f"Return code: {returncode}\n\n"
                "Synthesise the final result as JSON matching the output_schema."
            )

            synth_response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYNTH_SYSTEM_PROMPT},
                    {"role": "user", "content": synth_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            output = _parse_llm_json(synth_response.choices[0].message.content)

            # Attach raw execution details for UI display
            output["_code"] = code
            output["_stdout_preview"] = stdout[:500] if stdout else ""

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
