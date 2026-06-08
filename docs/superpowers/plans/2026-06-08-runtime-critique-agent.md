# Runtime Critique Agent Node — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `Critique` node type that the pipeline designer places in the DAG; at both design time and run time it acts as an independent LLM-based domain-expert that validates the preceding agent(s), sends fix instructions back to the agent (never fixes code itself), and repeats min 3 iterations (clean) / max 5 (error) before allowing the pipeline to proceed.

**Architecture:** `CritiqueNodeExecutor` in a new `runtime_critique.py` handles the critique loop for run time. `ws_design.py` gets a parallel critique-node path for design time. Both share the same `CritiqueNodeExecutor` logic and LLM prompt. Normal task agents (`agent_type: "task"` or absent) are completely unchanged.

**Tech Stack:** Python 3.12, OpenAI-compatible Gemini SDK, FastAPI WebSockets, Pydantic, pytest-asyncio

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/agents/runtime_critique.py` | **Create** | `CritiqueNodeExecutor` — LLM domain-expert critique loop |
| `backend/app/prompts/critique_runtime.py` | **Create** | Design-time and run-time LLM prompt builders |
| `backend/app/api/ws_run.py` | **Modify** | Detect `agent_type=critique`, dispatch to `CritiqueNodeExecutor` |
| `backend/app/api/ws_design.py` | **Modify** | Detect `agent_type=critique` in blueprint, dispatch to `CritiqueNodeExecutor` |
| `backend/tests/test_runtime_critique.py` | **Create** | TDD tests for critique loop |
| `backend/tests/test_ws_run_critique.py` | **Create** | Integration tests for ws_run critique dispatch |

---

## Task 1: Prompts for runtime critique

**Files:**
- Create: `backend/app/prompts/critique_runtime.py`

- [ ] **Step 1.1: Write failing test**

```python
# backend/tests/test_runtime_critique.py
import pytest
from app.prompts.critique_runtime import build_design_critique_prompt, build_run_critique_prompt

def test_design_critique_prompt_contains_agent_description():
    prompt = build_design_critique_prompt(
        agent_name="CloneRepository",
        agent_description="Clones a git repository to a local path",
        input_schema={"clone_url": {"type": "string"}},
        output_schema={"repository_path": {"type": "string"}},
    )
    assert "CloneRepository" in prompt
    assert "git" in prompt.lower() or "clone" in prompt.lower()
    assert "industry" in prompt.lower() or "standard" in prompt.lower()

def test_run_critique_prompt_contains_execution_results():
    prompt = build_run_critique_prompt(
        agent_name="IdentifyLogStorage",
        agent_description="Identifies the log storage mechanism",
        input_schema={"repository_path": {"type": "string"}},
        output_schema={"log_storage_mechanism": {"type": "string"}},
        actual_inputs={"REPOSITORY_PATH": "/tmp/tmpabc"},
        code="import os\npath = os.environ['REPOSITORY_PATH']",
        stdout='{"log_storage_mechanism": "file"}',
        stderr="",
        returncode=0,
    )
    assert "IdentifyLogStorage" in prompt
    assert "/tmp/tmpabc" in prompt
    assert "APPROVED" in prompt
    assert "NEEDS_FIX" in prompt

def test_run_critique_prompt_flags_output_schema_as_env_var():
    prompt = build_run_critique_prompt(
        agent_name="TestAgent",
        agent_description="Detects log events",
        input_schema={"repository_path": {"type": "string"}},
        output_schema={"detected_log_event": {"type": "string"}},
        actual_inputs={"REPOSITORY_PATH": "/tmp/repo"},
        code="import os\nevent = os.environ['DETECTED_LOG_EVENT']",
        stdout="",
        stderr="KeyError: 'DETECTED_LOG_EVENT'",
        returncode=1,
    )
    assert "output" in prompt.lower()
    assert "input" in prompt.lower()
    assert "DETECTED_LOG_EVENT" in prompt
```

- [ ] **Step 1.2: Run to confirm RED**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/test_runtime_critique.py -v
```
Expected: `ImportError: No module named 'app.prompts.critique_runtime'`

- [ ] **Step 1.3: Create the prompts file**

```python
# backend/app/prompts/critique_runtime.py
"""LLM prompts for the runtime Critique Agent node.

Two variants:
- build_design_critique_prompt: validates agent spec/schema at design time
- build_run_critique_prompt:    validates execution output at run time
"""
import json


_CRITIQUE_SYSTEM = """You are a world-class expert reviewing an AI agent.
Your job: evaluate the agent against industry best standards for its specific domain.
Be precise and actionable. Never fix the code yourself — only give instructions.

Return ONLY valid JSON:
{{
  "verdict": "APPROVED" or "NEEDS_FIX",
  "quality_score": <1-10>,
  "issues": ["specific issue 1", ...],
  "fix_instructions": "Precise instructions for the agent to fix its approach. Empty string if APPROVED."
}}"""


def build_design_critique_prompt(
    agent_name: str,
    agent_description: str,
    input_schema: dict,
    output_schema: dict,
) -> str:
    return f"""{_CRITIQUE_SYSTEM}

MODE: Design-time — validate the agent's specification and schema.

Agent: {agent_name}
Description: {agent_description}
Input Schema: {json.dumps(input_schema, indent=2)}
Output Schema: {json.dumps(output_schema, indent=2)}

Evaluate:
1. Does the description clearly describe ONE atomic task aligned with industry standards for this domain?
2. Is the input schema complete — are all required inputs present?
3. Is the output schema meaningful — does it capture what this agent should produce?
4. Are there schema fields that belong in the OTHER schema (e.g. output fields used as inputs)?
5. Is the agent's approach industry-standard for: {agent_description}?

If verdict is NEEDS_FIX, fix_instructions must tell the agent exactly what to change in its spec/schema."""


def build_run_critique_prompt(
    agent_name: str,
    agent_description: str,
    input_schema: dict,
    output_schema: dict,
    actual_inputs: dict,
    code: str,
    stdout: str,
    stderr: str,
    returncode: int,
) -> str:
    output_keys = list(output_schema.keys())
    input_keys_upper = [k.upper() for k in input_schema.keys()]

    return f"""{_CRITIQUE_SYSTEM}

MODE: Run-time — validate the agent's execution output.

Agent: {agent_name}
Description: {agent_description}
Input Schema: {json.dumps(input_schema, indent=2)}
Output Schema: {json.dumps(output_schema, indent=2)}

Actual inputs available (as env vars): {json.dumps(actual_inputs, indent=2)}
Code executed:
```python
{code[:1000]}
```
Stdout: {stdout[:500] or "(empty)"}
Stderr: {stderr[:500] or "(none)"}
Return code: {returncode}

CRITICAL CHECKS:
- Output schema fields ({output_keys}) must be PRODUCED by the agent, not read from os.environ
- Only input schema fields ({input_keys_upper}) should be read from os.environ
- Reading an output field as os.environ['FIELD'] is ALWAYS wrong

Evaluate:
1. Does the code correctly read only INPUT schema fields from os.environ? (not output fields)
2. Does the output fulfil the agent's stated purpose: {agent_description}?
3. Is the approach industry-standard for this domain?
4. Are there security, reliability, or correctness issues?
5. Is the output complete and actionable (not 'unknown' or empty)?

If verdict is NEEDS_FIX, fix_instructions must tell the agent exactly how to fix its code."""
```

- [ ] **Step 1.4: Run tests — GREEN**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/test_runtime_critique.py::test_design_critique_prompt_contains_agent_description tests/test_runtime_critique.py::test_run_critique_prompt_contains_execution_results tests/test_runtime_critique.py::test_run_critique_prompt_flags_output_schema_as_env_var -v
```
Expected: 3 PASSED

- [ ] **Step 1.5: Commit**

```bash
git add backend/app/prompts/critique_runtime.py backend/tests/test_runtime_critique.py
git commit -m "feat: add runtime critique LLM prompts (design-time and run-time variants)"
```

---

## Task 2: CritiqueNodeExecutor class

**Files:**
- Create: `backend/app/agents/runtime_critique.py`
- Modify: `backend/tests/test_runtime_critique.py` (add new tests)

- [ ] **Step 2.1: Add failing tests**

Append to `backend/tests/test_runtime_critique.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.runtime_critique import CritiqueNodeExecutor, CritiqueLoopResult

# ── CritiqueNodeExecutor ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_critique_approves_and_returns_after_min_iterations():
    """Approved output should still run min_iterations times."""
    executor = CritiqueNodeExecutor(api_key="fake", model="gemini")
    approved = {"verdict": "APPROVED", "quality_score": 9.0, "issues": [], "fix_instructions": ""}

    with patch.object(executor, "_call_critique_llm", new=AsyncMock(return_value=approved)):
        result = await executor.run_design_critique(
            agent_spec={
                "agent_id": "a1", "agent_name": "CloneRepo",
                "description": "Clones a git repo",
                "input_schema": {"clone_url": {"type": "string"}},
                "output_schema": {"repository_path": {"type": "string"}},
            },
            min_iterations=3,
            max_iterations=5,
        )

    assert result.verdict == "APPROVED"
    assert result.iterations == 3  # ran min_iterations times


@pytest.mark.asyncio
async def test_critique_needs_fix_calls_on_fix_callback():
    """NEEDS_FIX should invoke on_fix_needed callback with instructions."""
    executor = CritiqueNodeExecutor(api_key="fake", model="gemini")
    needs_fix = {
        "verdict": "NEEDS_FIX", "quality_score": 3.0,
        "issues": ["Output field used as input env var"],
        "fix_instructions": "Remove os.environ['DETECTED_LOG_EVENT'] — produce that field instead",
    }
    approved = {"verdict": "APPROVED", "quality_score": 9.0, "issues": [], "fix_instructions": ""}

    responses = [needs_fix, needs_fix, approved, approved, approved]
    call_count = 0
    fix_calls = []

    async def mock_llm(*args, **kwargs):
        nonlocal call_count
        r = responses[call_count]
        call_count += 1
        return r

    async def on_fix(instructions: str, iteration: int):
        fix_calls.append((instructions, iteration))

    with patch.object(executor, "_call_critique_llm", new=mock_llm):
        result = await executor.run_design_critique(
            agent_spec={
                "agent_id": "a1", "agent_name": "DetectLog",
                "description": "Detects log events",
                "input_schema": {"repository_path": {"type": "string"}},
                "output_schema": {"detected_log_event": {"type": "string"}},
            },
            min_iterations=3,
            max_iterations=5,
            on_fix_needed=on_fix,
        )

    assert len(fix_calls) == 2
    assert "DETECTED_LOG_EVENT" in fix_calls[0][0]
    assert result.verdict == "APPROVED"


@pytest.mark.asyncio
async def test_critique_fails_after_max_iterations():
    """If NEEDS_FIX persists through max_iterations, result is NEEDS_FIX."""
    executor = CritiqueNodeExecutor(api_key="fake", model="gemini")
    needs_fix = {
        "verdict": "NEEDS_FIX", "quality_score": 2.0,
        "issues": ["Always broken"],
        "fix_instructions": "Fix it",
    }

    with patch.object(executor, "_call_critique_llm", new=AsyncMock(return_value=needs_fix)):
        result = await executor.run_design_critique(
            agent_spec={
                "agent_id": "a1", "agent_name": "BrokenAgent",
                "description": "Always broken",
                "input_schema": {}, "output_schema": {},
            },
            min_iterations=3,
            max_iterations=5,
        )

    assert result.verdict == "NEEDS_FIX"
    assert result.iterations == 5


@pytest.mark.asyncio
async def test_run_critique_passes_execution_context_to_llm():
    """run_exec_critique passes code/stdout/stderr to the LLM."""
    executor = CritiqueNodeExecutor(api_key="fake", model="gemini")
    approved = {"verdict": "APPROVED", "quality_score": 8.0, "issues": [], "fix_instructions": ""}
    captured_prompts = []

    async def mock_llm(prompt: str):
        captured_prompts.append(prompt)
        return approved

    with patch.object(executor, "_call_critique_llm", new=mock_llm):
        await executor.run_exec_critique(
            agent_spec={
                "agent_id": "a1", "agent_name": "Identify",
                "description": "Identifies log storage",
                "input_schema": {"repository_path": {"type": "string"}},
                "output_schema": {"log_storage_mechanism": {"type": "string"}},
            },
            actual_inputs={"REPOSITORY_PATH": "/tmp/tmpabc"},
            code="import os\npath = os.environ['REPOSITORY_PATH']",
            stdout='{"log_storage_mechanism": "file"}',
            stderr="",
            returncode=0,
            min_iterations=3,
            max_iterations=5,
        )

    assert any("/tmp/tmpabc" in p for p in captured_prompts)
```

- [ ] **Step 2.2: Run to confirm RED**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/test_runtime_critique.py -v -k "executor or critique_approves or critique_needs or critique_fails or run_critique_passes"
```
Expected: `ImportError: No module named 'app.agents.runtime_critique'`

- [ ] **Step 2.3: Create CritiqueNodeExecutor**

```python
# backend/app/agents/runtime_critique.py
"""Runtime Critique Agent Node executor.

CritiqueNodeExecutor is called when ws_run.py or ws_design.py encounters
a node with agent_type='critique'. It runs an LLM-based domain-expert
critique loop against the preceding agent's spec (design time) or
execution output (run time).

It never fixes code. It sends fix instructions to on_fix_needed callback,
which re-runs the target agent.
"""
import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from openai import AsyncOpenAI

from app.agents.llm_utils import _repair_json_escapes
from app.config import settings
from app.prompts.critique_runtime import build_design_critique_prompt, build_run_critique_prompt

import json

logger = logging.getLogger(__name__)


@dataclass
class CritiqueLoopResult:
    verdict: str          # "APPROVED" | "NEEDS_FIX"
    quality_score: float
    iterations: int
    issues: list[str] = field(default_factory=list)
    fix_instructions: str = ""


FixCallback = Callable[[str, int], Awaitable[None]]


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
        assert self.client is not None, "Cannot call LLM with fake client"
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        raw = _repair_json_escapes(response.choices[0].message.content)
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
                agent_spec.get("agent_name"), iteration, max_iterations,
                verdict, last_result.get("quality_score", 0),
            )

            if on_event:
                await on_event("CRITIQUE_ITERATION", {
                    "agent_id": agent_spec.get("agent_id"),
                    "iteration": iteration,
                    "verdict": verdict,
                    "issues": issues,
                    "quality_score": last_result.get("quality_score", 0),
                    "mode": "design",
                })

            if verdict == "NEEDS_FIX" and on_fix_needed:
                await on_fix_needed(fix_instructions, iteration)

            if verdict == "APPROVED" and iteration >= min_iterations:
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
        code: str,
        stdout: str,
        stderr: str,
        returncode: int,
        min_iterations: int = 3,
        max_iterations: int = 5,
        on_fix_needed: FixCallback | None = None,
        on_event=None,
    ) -> CritiqueLoopResult:
        """Critique an agent's execution output at run time."""
        last_result: dict = {}

        for iteration in range(1, max_iterations + 1):
            prompt = build_run_critique_prompt(
                agent_name=agent_spec.get("agent_name", ""),
                agent_description=agent_spec.get("description", ""),
                input_schema=agent_spec.get("input_schema", {}),
                output_schema=agent_spec.get("output_schema", {}),
                actual_inputs=actual_inputs,
                code=code,
                stdout=stdout,
                stderr=stderr,
                returncode=returncode,
            )
            last_result = await self._call_critique_llm(prompt)
            verdict = last_result.get("verdict", "NEEDS_FIX")
            issues = last_result.get("issues", [])
            fix_instructions = last_result.get("fix_instructions", "")

            logger.info(
                "[critique][run] %s iteration %d/%d: %s (score=%.1f)",
                agent_spec.get("agent_name"), iteration, max_iterations,
                verdict, last_result.get("quality_score", 0),
            )

            if on_event:
                await on_event("CRITIQUE_ITERATION", {
                    "agent_id": agent_spec.get("agent_id"),
                    "iteration": iteration,
                    "verdict": verdict,
                    "issues": issues,
                    "quality_score": last_result.get("quality_score", 0),
                    "mode": "run",
                })

            if verdict == "NEEDS_FIX" and on_fix_needed:
                await on_fix_needed(fix_instructions, iteration)

            if verdict == "APPROVED" and iteration >= min_iterations:
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
```

- [ ] **Step 2.4: Run tests — GREEN**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/test_runtime_critique.py -v
```
Expected: All tests PASS

- [ ] **Step 2.5: Commit**

```bash
git add backend/app/agents/runtime_critique.py backend/tests/test_runtime_critique.py
git commit -m "feat: CritiqueNodeExecutor — LLM domain-expert critique loop (design + run time)"
```

---

## Task 3: Wire Critique node into ws_run.py (run time)

**Files:**
- Modify: `backend/app/api/ws_run.py`
- Create: `backend/tests/test_ws_run_critique.py`

- [ ] **Step 3.1: Write failing tests**

```python
# backend/tests/test_ws_run_critique.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_critique_node_triggers_rerun_on_needs_fix(monkeypatch):
    """When a critique node finds NEEDS_FIX, it calls the target agent again with fix instructions."""
    from app.api.ws_run import _run_critique_node

    target_agent_spec = {
        "agent_id": "identify_001",
        "agent_name": "IdentifyLogStorage",
        "agent_type": "task",
        "description": "Identifies log storage",
        "input_schema": {"repository_path": {"type": "string"}},
        "output_schema": {"log_storage_mechanism": {"type": "string"}},
        "depends_on": [],
    }
    critique_spec = {
        "agent_id": "critique_001",
        "agent_name": "CritiqueLogStorage",
        "agent_type": "critique",
        "description": "Validates log storage identification",
        "depends_on": ["identify_001"],
    }

    results_store = {}
    rerun_calls = []

    async def mock_rerun(agent_spec, context, fix_instructions):
        rerun_calls.append(fix_instructions)
        results_store["identify_001"] = MagicMock(
            status="completed",
            output={"log_storage_mechanism": "cloudwatch"},
            error=None,
        )

    from app.agents.runtime_critique import CritiqueLoopResult
    mock_executor = MagicMock()
    mock_executor.run_exec_critique = AsyncMock(return_value=CritiqueLoopResult(
        verdict="APPROVED", quality_score=9.0, iterations=3,
    ))

    with patch("app.api.ws_run.CritiqueNodeExecutor", return_value=mock_executor):
        await _run_critique_node(
            critique_spec=critique_spec,
            ordered_agents=[target_agent_spec],
            results=results_store,
            context={"REPOSITORY_PATH": "/tmp/tmpabc"},
            send=AsyncMock(),
            rerun_agent=mock_rerun,
        )

    mock_executor.run_exec_critique.assert_called_once()


@pytest.mark.asyncio
async def test_critique_node_skipped_if_no_depends_on():
    """Critique node with empty depends_on should complete without calling LLM."""
    from app.api.ws_run import _run_critique_node
    from app.agents.runtime_critique import CritiqueLoopResult

    mock_executor = MagicMock()
    mock_executor.run_exec_critique = AsyncMock(return_value=CritiqueLoopResult(
        verdict="APPROVED", quality_score=9.0, iterations=3,
    ))

    with patch("app.api.ws_run.CritiqueNodeExecutor", return_value=mock_executor):
        await _run_critique_node(
            critique_spec={"agent_id": "c1", "agent_name": "C", "agent_type": "critique", "depends_on": []},
            ordered_agents=[],
            results={},
            context={},
            send=AsyncMock(),
            rerun_agent=AsyncMock(),
        )

    mock_executor.run_exec_critique.assert_not_called()
```

- [ ] **Step 3.2: Run to confirm RED**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/test_ws_run_critique.py -v
```
Expected: `ImportError: cannot import name '_run_critique_node' from 'app.api.ws_run'`

- [ ] **Step 3.3: Add `_run_critique_node` to ws_run.py**

Add these imports at top of `backend/app/api/ws_run.py`:
```python
from app.agents.runtime_critique import CritiqueNodeExecutor
from app.agents.agent_executor import AgentExecutorAgent
```

Add this function before `ws_run_handler`:
```python
async def _run_critique_node(
    critique_spec: dict,
    ordered_agents: list[dict],
    results: dict,
    context: dict,
    send,
    rerun_agent,
) -> None:
    """Execute a critique node: validate each depends_on agent's result via LLM."""
    agent_map = {a["agent_id"]: a for a in ordered_agents}
    deps = critique_spec.get("depends_on", [])

    if not deps:
        await send("AGENT_RESULT", {
            "agent_id": critique_spec["agent_id"],
            "agent_name": critique_spec.get("agent_name", "Critique"),
            "status": "completed",
            "output": {"critique_verdict": "SKIPPED", "reason": "no depends_on"},
            "error": None,
            "duration_ms": 0,
        })
        return

    executor = CritiqueNodeExecutor()
    all_approved = True

    for target_id in deps:
        target_spec = agent_map.get(target_id)
        if not target_spec:
            continue

        target_result = results.get(target_id)
        if not target_result:
            continue

        fix_instructions_accumulator = []

        async def on_fix(instructions: str, iteration: int):
            fix_instructions_accumulator.append(instructions)
            await send("CRITIQUE_FIX", {
                "agent_id": critique_spec["agent_id"],
                "target_agent_id": target_id,
                "iteration": iteration,
                "fix_instructions": instructions,
            })
            await rerun_agent(target_spec, context, instructions)
            # Refresh result after rerun
            refreshed = results.get(target_id)
            if refreshed:
                nonlocal target_result
                target_result = refreshed

        result = await executor.run_exec_critique(
            agent_spec=target_spec,
            actual_inputs=context,
            code=target_result.output.get("_code", "") if target_result.output else "",
            stdout=target_result.output.get("_stdout_preview", "") if target_result.output else "",
            stderr=target_result.error or "",
            returncode=0 if target_result.status == "completed" else 1,
            min_iterations=3,
            max_iterations=5 if target_result.status == "failed" else 3,
            on_fix_needed=on_fix,
            on_event=send,
        )

        if result.verdict != "APPROVED":
            all_approved = False

        await send("AGENT_RESULT", {
            "agent_id": critique_spec["agent_id"],
            "agent_name": critique_spec.get("agent_name", "Critique"),
            "status": "completed" if result.verdict == "APPROVED" else "failed",
            "output": {
                "critique_verdict": result.verdict,
                "quality_score": result.quality_score,
                "iterations": result.iterations,
                "issues": result.issues,
                "target_agent": target_id,
            },
            "error": result.fix_instructions if result.verdict == "NEEDS_FIX" else None,
            "duration_ms": 0,
        })
```

- [ ] **Step 3.4: Update `ws_run_handler` to dispatch critique nodes**

In `ws_run_handler`, replace the existing agent loop with this pattern:

Find this block in `ws_run.py`:
```python
        for agent_spec in ordered_agents:
            agent_id = agent_spec["agent_id"]

            # Skip this agent if any of its dependencies failed
```

Add critique dispatch at the start of the loop body, after the failed-dep check:
```python
            # ── Critique node dispatch ────────────────────────────────────────
            if agent_spec.get("agent_type") == "critique":
                async def _rerun(spec, ctx, fix_instr):
                    extra_hint = f"\n\nCRITIQUE FIX REQUIRED:\n{fix_instr}"
                    rerun_result = await executor.execute(
                        {**spec, "_critique_fix": fix_instr},
                        {**ctx, "_critique_fix_instructions": extra_hint},
                        on_code_event=_on_code_event,
                    )
                    results[spec["agent_id"]] = rerun_result
                    if rerun_result.status != "failed":
                        context.update(rerun_result.output)

                await _run_critique_node(
                    critique_spec=agent_spec,
                    ordered_agents=ordered_agents,
                    results={r.agent_id: r for r in results},
                    context=context,
                    send=lambda t, d: send(t, d),
                    rerun_agent=_rerun,
                )
                continue
```

- [ ] **Step 3.5: Update PLAN_SYSTEM_PROMPT in agent_executor.py to inject critique fix instructions**

In `backend/app/agents/agent_executor.py`, update `plan_prompt` construction to include critique fix instructions if present:

```python
            plan_prompt = (
                f"Agent: {agent_name}\n"
                f"Description: {agent_spec.get('description', '')}\n"
                f"Input Schema: {json.dumps(agent_spec.get('input_schema', {}), indent=2)}\n"
                f"Output Schema: {json.dumps(agent_spec.get('output_schema', {}), indent=2)}\n"
                f"Available Inputs: {json.dumps(context_inputs, indent=2)}\n\n"
                "Decide: NO_CODE_NEEDED (return output directly) or EXECUTE_CODE (write Python)."
            )
            # Inject critique fix instructions if this is a critique-driven re-run
            critique_fix = context_inputs.get("_critique_fix_instructions", "")
            if critique_fix:
                plan_prompt += f"\n\nCRITIQUE AGENT INSTRUCTION:\n{critique_fix}\nYou MUST address this in your implementation."
```

- [ ] **Step 3.6: Run tests — GREEN**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/test_ws_run_critique.py tests/test_runtime_critique.py -v
```
Expected: All PASS

- [ ] **Step 3.7: Run full suite**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/ -q
```
Expected: 70+ passed, 0 failed

- [ ] **Step 3.8: Commit**

```bash
git add backend/app/api/ws_run.py backend/tests/test_ws_run_critique.py
git commit -m "feat: wire Critique node into ws_run — LLM domain-expert validation at run time"
```

---

## Task 4: Wire Critique node into ws_design.py (design time)

**Files:**
- Modify: `backend/app/api/ws_design.py`

- [ ] **Step 4.1: Write failing test**

Append to `backend/tests/test_ws_run_critique.py`:

```python
@pytest.mark.asyncio
async def test_design_critique_node_calls_design_critique():
    """Critique node in design blueprint triggers run_design_critique."""
    from app.api.ws_design import _run_design_critique_node
    from app.agents.runtime_critique import CritiqueLoopResult

    mock_executor = MagicMock()
    mock_executor.run_design_critique = AsyncMock(return_value=CritiqueLoopResult(
        verdict="APPROVED", quality_score=8.5, iterations=3,
    ))
    redesign_calls = []

    async def mock_redesign(spec, fix_instructions):
        redesign_calls.append((spec["agent_id"], fix_instructions))

    with patch("app.api.ws_design.CritiqueNodeExecutor", return_value=mock_executor):
        await _run_design_critique_node(
            critique_spec={
                "agent_id": "c1", "agent_name": "CritiqueClone",
                "agent_type": "critique", "depends_on": ["clone_001"],
            },
            agent_specs=[{
                "agent_id": "clone_001", "agent_name": "CloneRepo",
                "description": "Clones a git repo",
                "input_schema": {"clone_url": {"type": "string"}},
                "output_schema": {"repository_path": {"type": "string"}},
            }],
            send=AsyncMock(),
            redesign_agent=mock_redesign,
        )

    mock_executor.run_design_critique.assert_called_once()
```

- [ ] **Step 4.2: Run to confirm RED**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/test_ws_run_critique.py::test_design_critique_node_calls_design_critique -v
```
Expected: `ImportError: cannot import name '_run_design_critique_node'`

- [ ] **Step 4.3: Add `_run_design_critique_node` to ws_design.py**

Add import at top of `backend/app/api/ws_design.py`:
```python
from app.agents.runtime_critique import CritiqueNodeExecutor
```

Add function before `ws_design_handler`:
```python
async def _run_design_critique_node(
    critique_spec: dict,
    agent_specs: list[dict],
    send,
    redesign_agent,
) -> None:
    """Execute a critique node against agent specs during pipeline design."""
    agent_map = {a["agent_id"]: a for a in agent_specs}
    deps = critique_spec.get("depends_on", [])
    executor = CritiqueNodeExecutor()

    for target_id in deps:
        target_spec = agent_map.get(target_id)
        if not target_spec:
            continue

        async def on_fix(instructions: str, iteration: int):
            await send("CRITIQUE_FIX", {
                "agent_id": critique_spec["agent_id"],
                "target_agent_id": target_id,
                "iteration": iteration,
                "fix_instructions": instructions,
            })
            await redesign_agent(target_spec, instructions)

        result = await executor.run_design_critique(
            agent_spec=target_spec,
            min_iterations=3,
            max_iterations=5,
            on_fix_needed=on_fix,
            on_event=send,
        )

        await send("AGENT_RESULT", {
            "agent_id": critique_spec["agent_id"],
            "agent_name": critique_spec.get("agent_name", "Critique"),
            "status": "completed" if result.verdict == "APPROVED" else "failed",
            "output": {
                "critique_verdict": result.verdict,
                "quality_score": result.quality_score,
                "iterations": result.iterations,
                "issues": result.issues,
                "target_agent": target_id,
            },
            "error": result.fix_instructions if result.verdict == "NEEDS_FIX" else None,
            "duration_ms": 0,
        })
```

- [ ] **Step 4.4: Wire into ws_design_handler loop**

In `ws_design_handler`, in the agent loop, add critique dispatch before the existing `agent = await producer.produce(...)` call:

```python
        for i, agent_spec in enumerate(blueprint.get("agents", []), 1):
            # ── Critique node dispatch ────────────────────────────────────────
            if agent_spec.get("agent_type") == "critique":
                async def _redesign(spec, fix_instructions):
                    # Re-produce the agent with critique fix hint
                    revised = await producer.produce(
                        {**spec, "critique_fix": fix_instructions},
                        "design_time", pipeline_id, {}, on_event=send,
                    )
                    # Update blueprint in place
                    for j, a in enumerate(blueprint["agents"]):
                        if a["agent_id"] == spec["agent_id"]:
                            blueprint["agents"][j] = revised.model_dump()

                await _run_design_critique_node(
                    critique_spec=agent_spec,
                    agent_specs=blueprint.get("agents", []),
                    send=send,
                    redesign_agent=_redesign,
                )
                continue
            # ... existing agent_name / producer.produce / run_critique_loop logic ...
```

- [ ] **Step 4.5: Run tests — GREEN**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/test_ws_run_critique.py -v
```
Expected: All PASS

- [ ] **Step 4.6: Run full suite**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/ -q
```
Expected: 75+ passed, 0 failed

- [ ] **Step 4.7: Commit**

```bash
git add backend/app/api/ws_design.py backend/tests/test_ws_run_critique.py
git commit -m "feat: wire Critique node into ws_design — LLM domain-expert validation at design time"
```

---

## Task 5: Deploy and verify

- [ ] **Step 5.1: Run full test suite one final time**

```
cd backend && .venv\Scripts\python.exe -m pytest tests/ -v
```
Expected: 75+ passed, 0 failed

- [ ] **Step 5.2: Deploy**

```
cd C:\Users\schinta\AgentMaster && .\deploy.ps1
```

- [ ] **Step 5.3: Commit docs**

```bash
git add docs/
git commit -m "docs: runtime critique agent — spec and plan"
git push origin main
```
