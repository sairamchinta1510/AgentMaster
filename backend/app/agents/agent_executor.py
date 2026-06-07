# backend/app/agents/agent_executor.py
import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from openai import AsyncOpenAI

from app.agents.code_executor import execute_python_code
from app.agents.code_reviewer import review_and_fix_code
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

OPTION A — Pure reasoning ONLY when ALL output values can be derived directly from the inputs with certainty:
Return ONLY this JSON:
{"action": "NO_CODE_NEEDED", "output": {<json matching output_schema>}}

OPTION B — Required whenever the task involves reading files, scanning directories, calling APIs, or any real-world data access:
Return ONLY this JSON:
{"action": "EXECUTE_CODE", "code": "<python code string>", "credential_keys": ["KEY1"]}

IMPORTANT: If any input contains a file path (repository_path, file_path, log_path, etc.) you MUST use
EXECUTE_CODE to read and analyse the actual files — NEVER use NO_CODE_NEEDED for file-based tasks.

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

# Sentinel phrases that indicate the LLM gave a vague non-answer instead of real data
_VAGUE_OUTPUT_PHRASES = [
    "not directly available",
    "not available",
    "beyond the scope",
    "requires deeper analysis",
    "cannot be determined",
    "would need to",
    "further analysis",
    "unknown",
]

# Input key suffixes that indicate a file/directory path — must trigger EXECUTE_CODE
_PATH_INPUT_KEYS = {"path", "dir", "directory", "file", "repo", "repository"}


def _is_vague_output(output: dict) -> bool:
    """Return True if any string output value contains a sentinel non-answer phrase."""
    for v in output.values():
        if isinstance(v, str):
            lower = v.lower()
            if any(phrase in lower for phrase in _VAGUE_OUTPUT_PHRASES):
                return True
    return False


def _has_path_inputs(context_inputs: dict) -> bool:
    """Return True if any input key looks like a file/directory path."""
    for key in context_inputs:
        key_lower = key.lower()
        if any(suffix in key_lower for suffix in _PATH_INPUT_KEYS):
            return True
    return False


# Callback type: called when executor enters a new code phase
CodeEventCallback = Callable[[str, str, str | None], Awaitable[None]]
# Args: (agent_id, phase, code_preview)
# phase: "planning" | "reviewing" | "executing" | "synthesising" | "fallback"


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

                # Output quality critique: if the LLM gave a vague non-answer
                # (especially for file-based tasks), force a code execution retry
                if _is_vague_output(output) or _has_path_inputs(context_inputs):
                    logger.warning(
                        "[%s] NO_CODE_NEEDED produced vague/incomplete output or "
                        "has path inputs — forcing EXECUTE_CODE retry",
                        agent_id,
                    )
                    retry_prompt = (
                        plan_prompt
                        + "\n\nCRITIQUE: The previous NO_CODE_NEEDED response was insufficient. "
                        + "You MUST use EXECUTE_CODE to read and analyse the actual files/data. "
                        + "Do NOT attempt to answer from reasoning alone when file paths are provided."
                    )
                    retry_response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": PLAN_SYSTEM_PROMPT},
                            {"role": "user", "content": retry_prompt},
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.2,
                    )
                    plan = _parse_llm_json(retry_response.choices[0].message.content)
                    if plan.get("action") == "NO_CODE_NEEDED":
                        # LLM still refused to run code — accept output as-is
                        output = plan.get("output", output)
                        duration_ms = int(time.time() * 1000) - start_ms
                        return AgentResult(
                            agent_id=agent_id, agent_name=agent_name,
                            status="completed", output=output, duration_ms=duration_ms,
                        )
                    # Fall through to EXEC path with new plan
                else:
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

            # Inject ALL context inputs as uppercased env vars so generated code
            # can read any input (paths, URLs, names, credentials) via os.environ.
            # e.g. context_inputs["repository_path"] -> os.environ["REPOSITORY_PATH"]
            env_vars: dict[str, str] = {
                k.upper(): str(v)
                for k, v in context_inputs.items()
                if not k.startswith("_") and v is not None
            }

            MAX_RETRIES = 3
            last_error: str = ""
            plan_prompt_base = plan_prompt  # keep for retry re-plan

            for attempt in range(1, MAX_RETRIES + 1):
                code_preview = code[:200] if code else None

                # ── REVIEW phase ─────────────────────────────────────────────
                await emit("reviewing", code_preview)
                code, review_changes = await review_and_fix_code(
                    code, env_vars, self.client, self.model
                )
                if review_changes:
                    logger.info(
                        "[%s] attempt %d: reviewer fixed %d issue(s): %s",
                        agent_id, attempt, len(review_changes), review_changes,
                    )

                await emit("executing", code[:200] if code else None)
                stdout, stderr, returncode = await execute_python_code(code, env_vars)

                if returncode == 0:
                    break  # success

                # Execution failed — retry with error context injected into re-plan
                last_error = stderr or stdout or f"Exit code {returncode}"
                logger.warning(
                    "[%s] attempt %d/%d failed: %s",
                    agent_id, attempt, MAX_RETRIES, last_error[:200],
                )

                if attempt < MAX_RETRIES:
                    await emit("planning")  # signal UI we're re-planning
                    retry_prompt = (
                        plan_prompt_base
                        + f"\n\nPREVIOUS ATTEMPT FAILED (attempt {attempt}/{MAX_RETRIES}):\n"
                        + f"Error:\n{last_error[:500]}\n\n"
                        + "Fix the code and try again. Do NOT repeat the same mistake."
                    )
                    retry_response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": PLAN_SYSTEM_PROMPT},
                            {"role": "user", "content": retry_prompt},
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.2,
                    )
                    retry_plan = _parse_llm_json(retry_response.choices[0].message.content)
                    code = retry_plan.get("code", code)
            else:
                # All retries exhausted
                raise RuntimeError(
                    f"Agent failed after {MAX_RETRIES} attempts. Last error: {last_error[:300]}"
                )

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
