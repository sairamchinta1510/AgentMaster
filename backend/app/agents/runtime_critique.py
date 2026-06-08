"""Runtime Critique Agent Node executor.

CritiqueNodeExecutor is called when ws_run.py or ws_design.py encounters
a node with agent_type='critique'. It runs an LLM-based domain-expert
critique loop against the preceding agent's spec (design time) or
execution output (run time).

It never fixes code. It sends fix instructions to on_fix_needed callback,
which re-runs the target agent.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from openai import AsyncOpenAI

from app.agents.llm_utils import _repair_json_escapes
from app.config import settings
from app.prompts.critique_runtime import build_design_critique_prompt, build_run_critique_prompt

logger = logging.getLogger(__name__)


@dataclass
class CritiqueLoopResult:
    verdict: str
    quality_score: float
    iterations: int
    issues: list[str] = field(default_factory=list)
    fix_instructions: str = ""


FixCallback = Callable[[str, int], Awaitable[None]]


def _resolve_runtime_value(value: Any) -> Any:
    return value() if callable(value) else value


class CritiqueNodeExecutor:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        if api_key == "fake":
            self.client = None
            self.model = model or "fake"
        else:
            self.client = AsyncOpenAI(
                api_key=api_key or settings.active_api_key,
                base_url=settings.active_base_url,
            )
            self.model = model or settings.active_model

    async def _call_critique_llm(self, prompt: str) -> dict:
        if self.client is None:
            raise RuntimeError("Cannot call LLM with fake client")
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        content = response.choices[0].message.content or ""
        if not content.strip():
            raise ValueError("LLM returned empty content for critique")
        raw = _repair_json_escapes(content)
        return json.loads(raw)

    async def run_design_critique(
        self,
        agent_spec: dict,
        min_iterations: int = 3,
        max_iterations: int = 5,
        on_fix_needed: FixCallback | None = None,
        on_event=None,
    ) -> CritiqueLoopResult:
        """Critique an agent's spec/schema at design time."""
        last_result: dict = {}
        approved_seen = False

        for iteration in range(1, max_iterations + 1):
            prompt = build_design_critique_prompt(
                agent_name=agent_spec.get("agent_name", ""),
                agent_description=agent_spec.get("description", ""),
                input_schema=agent_spec.get("input_schema", {}),
                output_schema=agent_spec.get("output_schema", {}),
            )
            last_result = await self._call_critique_llm(prompt)
            verdict = last_result.get("verdict", "NEEDS_FIX")
            issues = last_result.get("issues", [])
            fix_instructions = last_result.get("fix_instructions", "")

            logger.info(
                "[critique][design] %s iteration %d/%d: %s (score=%.1f)",
                agent_spec.get("agent_name"),
                iteration,
                max_iterations,
                verdict,
                last_result.get("quality_score", 0),
            )

            if on_event:
                await on_event(
                    "CRITIQUE_ITERATION",
                    {
                        "agent_id": agent_spec.get("agent_id"),
                        "iteration": iteration,
                        "verdict": verdict,
                        "issues": issues,
                        "quality_score": last_result.get("quality_score", 0),
                        "mode": "design",
                    },
                )

            if verdict == "NEEDS_FIX" and on_fix_needed and not approved_seen:
                await on_fix_needed(fix_instructions, iteration)

            if verdict == "APPROVED":
                approved_seen = True
                if iteration >= min_iterations:
                    return CritiqueLoopResult(
                        verdict="APPROVED",
                        quality_score=last_result.get("quality_score", 0),
                        iterations=iteration,
                        issues=issues,
                    )

        return CritiqueLoopResult(
            verdict=last_result.get("verdict", "NEEDS_FIX"),
            quality_score=last_result.get("quality_score", 0),
            iterations=max_iterations,
            issues=last_result.get("issues", []),
            fix_instructions=last_result.get("fix_instructions", ""),
        )

    async def run_exec_critique(
        self,
        agent_spec: dict,
        actual_inputs: dict,
        code,
        stdout,
        stderr,
        returncode,
        min_iterations: int = 3,
        max_iterations: int = 5,
        on_fix_needed: FixCallback | None = None,
        on_event=None,
    ) -> CritiqueLoopResult:
        """Critique an agent's execution output at run time."""
        last_result: dict = {}
        approved_seen = False

        for iteration in range(1, max_iterations + 1):
            prompt = build_run_critique_prompt(
                agent_name=agent_spec.get("agent_name", ""),
                agent_description=agent_spec.get("description", ""),
                input_schema=agent_spec.get("input_schema", {}),
                output_schema=agent_spec.get("output_schema", {}),
                actual_inputs=actual_inputs,
                code=_resolve_runtime_value(code),
                stdout=_resolve_runtime_value(stdout),
                stderr=_resolve_runtime_value(stderr),
                returncode=_resolve_runtime_value(returncode),
            )
            last_result = await self._call_critique_llm(prompt)
            verdict = last_result.get("verdict", "NEEDS_FIX")
            issues = last_result.get("issues", [])
            fix_instructions = last_result.get("fix_instructions", "")

            logger.info(
                "[critique][run] %s iteration %d/%d: %s (score=%.1f)",
                agent_spec.get("agent_name"),
                iteration,
                max_iterations,
                verdict,
                last_result.get("quality_score", 0),
            )

            if on_event:
                await on_event(
                    "CRITIQUE_ITERATION",
                    {
                        "agent_id": agent_spec.get("agent_id"),
                        "iteration": iteration,
                        "verdict": verdict,
                        "issues": issues,
                        "quality_score": last_result.get("quality_score", 0),
                        "mode": "run",
                    },
                )

            if verdict == "NEEDS_FIX" and on_fix_needed and not approved_seen:
                await on_fix_needed(fix_instructions, iteration)

            if verdict == "APPROVED":
                approved_seen = True
                if iteration >= min_iterations:
                    return CritiqueLoopResult(
                        verdict="APPROVED",
                        quality_score=last_result.get("quality_score", 0),
                        iterations=iteration,
                        issues=issues,
                    )

        return CritiqueLoopResult(
            verdict=last_result.get("verdict", "NEEDS_FIX"),
            quality_score=last_result.get("quality_score", 0),
            iterations=max_iterations,
            issues=last_result.get("issues", []),
            fix_instructions=last_result.get("fix_instructions", ""),
        )
