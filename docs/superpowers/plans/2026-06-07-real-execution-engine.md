# Real Execution Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace LLM simulation in the executor with real code generation + subprocess execution, add scheduled/webhook pipeline triggers, and surface execution details in the UI.

**Architecture:** Each agent run goes through PLAN (LLM writes Python code) → EXEC (subprocess runs it) → SYNTH (LLM synthesises JSON output from real stdout). Pipelines carry a `trigger_config` decided by the design agent at design time; a scheduler fires scheduled pipelines and a webhook endpoint fires webhook pipelines. Credentials are stored per-pipeline and injected as env vars.

**Tech Stack:** Python asyncio subprocess, APScheduler 3.x, FastAPI router, boto3, google-cloud-logging, PyGithub, React/Zustand, Tailwind CSS

---

## File Map

**New backend files:**
- `backend/app/agents/code_executor.py` — subprocess runner (async, timeout, env injection, stdout cap)
- `backend/app/agents/headless_run.py` — non-WS pipeline execution for scheduler
- `backend/app/scheduler.py` — APScheduler setup, load/register/unregister pipeline schedules
- `backend/app/api/webhooks.py` — POST /api/webhooks/{pipeline_id}

**Modified backend files:**
- `backend/app/agents/agent_executor.py` — PLAN→EXEC→SYNTH loop; `on_code_event` callback
- `backend/app/api/ws_run.py` — pass `on_code_event` to executor; emit CODE_STATUS WS events
- `backend/app/models/pipeline.py` — add `default_inputs` JSON column to ORM
- `backend/app/api/routes/pipelines.py` — add PATCH /{id}/credentials endpoint; call `register_pipeline_schedule` on save
- `backend/app/prompts/master.py` — add `trigger_config` field to output format
- `backend/app/main.py` — start scheduler in lifespan; include webhooks router
- `backend/requirements.txt` — add boto3, google-cloud-logging, google-cloud-monitoring, PyGithub, kubernetes, apscheduler

**New frontend files:**
- `frontend/src/components/CredentialsPanel.tsx` — masked key-value credential editor

**Modified frontend files:**
- `frontend/src/types/index.ts` — add `CODE_STATUS` to `RunWSEvent`; add `TriggerConfig` type; update `PipelineSummary`
- `frontend/src/store/runStore.ts` — add `codeStatus: Record<string, CodeStatus>` to RunStore
- `frontend/src/hooks/useRunWS.ts` — handle `CODE_STATUS` events
- `frontend/src/components/AgentListColumn.tsx` — add phase line + expandable code/stdout in RunAgentList
- `frontend/src/pages/PipelinesPage.tsx` — trigger badge, webhook URL copy button, Credentials button
- `frontend/src/pages/DesignPage.tsx` — trigger_config chip in context bar after design completes

---

## Task 1: code_executor.py — Subprocess Runner

**Files:**
- Create: `backend/app/agents/code_executor.py`
- Test: `backend/tests/test_code_executor.py`

- [ ] **Step 1: Create `code_executor.py`**

```python
# backend/app/agents/code_executor.py
import asyncio
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_STDOUT_BYTES = 50 * 1024   # 50 KB
EXEC_TIMEOUT_SECONDS = 60


async def execute_python_code(
    code: str,
    env_vars: dict[str, str],
) -> tuple[str, str, int]:
    """
    Write code to /tmp, run in subprocess with env vars injected.
    Returns (stdout, stderr, returncode).
    Cleans up temp file on exit.
    """
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        prefix="agentmaster_",
        dir="/tmp",
        delete=False,
    ) as f:
        f.write(code)
        tmp_path = f.name

    try:
        env = {**os.environ, **{k: str(v) for k, v in env_vars.items()}}
        proc = await asyncio.create_subprocess_exec(
            "python",
            tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=EXEC_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return "", f"Execution timed out after {EXEC_TIMEOUT_SECONDS}s", 1

        stdout = stdout_bytes[:MAX_STDOUT_BYTES].decode("utf-8", errors="replace")
        stderr = stderr_bytes[:MAX_STDOUT_BYTES].decode("utf-8", errors="replace")
        return stdout, stderr, proc.returncode or 0
    finally:
        Path(tmp_path).unlink(missing_ok=True)
```

- [ ] **Step 2: Create test file**

```python
# backend/tests/test_code_executor.py
import asyncio
import pytest
from app.agents.code_executor import execute_python_code


@pytest.mark.asyncio
async def test_simple_print():
    stdout, stderr, rc = await execute_python_code('print("hello")', {})
    assert "hello" in stdout
    assert rc == 0


@pytest.mark.asyncio
async def test_env_var_injection():
    code = "import os; print(os.environ['MY_KEY'])"
    stdout, stderr, rc = await execute_python_code(code, {"MY_KEY": "secret_val"})
    assert "secret_val" in stdout
    assert rc == 0


@pytest.mark.asyncio
async def test_stderr_captured():
    code = "import sys; sys.stderr.write('oops\\n'); print('ok')"
    stdout, stderr, rc = await execute_python_code(code, {})
    assert "ok" in stdout
    assert "oops" in stderr


@pytest.mark.asyncio
async def test_timeout():
    from app.agents.code_executor import EXEC_TIMEOUT_SECONDS
    # Patch timeout to 1s for speed
    import app.agents.code_executor as mod
    original = mod.EXEC_TIMEOUT_SECONDS
    mod.EXEC_TIMEOUT_SECONDS = 1
    try:
        stdout, stderr, rc = await execute_python_code("import time; time.sleep(10)", {})
        assert "timed out" in stderr
        assert rc == 1
    finally:
        mod.EXEC_TIMEOUT_SECONDS = original
```

- [ ] **Step 3: Run tests**

```
cd backend && python -m pytest tests/test_code_executor.py -v
```

Expected: 4 PASSED

- [ ] **Step 4: Commit**

```
git add backend/app/agents/code_executor.py backend/tests/test_code_executor.py
git commit -m "feat: add code_executor subprocess runner with timeout and env injection"
```

---

## Task 2: Update agent_executor.py — PLAN→EXEC→SYNTH Loop

**Files:**
- Modify: `backend/app/agents/agent_executor.py`
- Test: `backend/tests/test_agent_executor.py` (new)

The executor now has two system prompts:
1. `PLAN_PROMPT` — LLM decides: return `NO_CODE_NEEDED` (direct JSON) or `EXECUTE_CODE` (Python code string)
2. `SYNTH_PROMPT` — LLM synthesises final JSON from real stdout

- [ ] **Step 1: Replace `agent_executor.py`**

```python
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
- Read credentials ONLY via os.environ["KEY_NAME"] — never hardcode values
- Print the result as a single JSON object to stdout (last print statement)
- Handle errors: print details to stderr, keep running
- Write files only to /tmp if needed
- NEVER run: rm -rf, kill, shutdown, or any destructive shell command
- Use only pre-installed packages: httpx, requests, boto3, google-cloud-logging,
  google-cloud-monitoring, PyGithub, kubernetes, json, os, sys, datetime
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
            plan = json.loads(plan_response.choices[0].message.content)

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

            # Extract credential values from context_inputs
            env_vars: dict[str, str] = {}
            for key in credential_keys:
                if key in context_inputs:
                    env_vars[key] = str(context_inputs[key])

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
            output = json.loads(synth_response.choices[0].message.content)

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
```

- [ ] **Step 2: Create test file**

```python
# backend/tests/test_agent_executor.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.agents.agent_executor import AgentExecutorAgent


AGENT_SPEC = {
    "agent_id": "agent_001",
    "agent_name": "TestAgent",
    "description": "Test agent",
    "input_schema": {"query": {"type": "string"}},
    "output_schema": {"result": {"type": "string"}},
}


@pytest.mark.asyncio
async def test_no_code_needed_path():
    executor = AgentExecutorAgent()
    plan_response = MagicMock()
    plan_response.choices[0].message.content = '{"action": "NO_CODE_NEEDED", "output": {"result": "hello"}}'

    with patch.object(executor.client.chat.completions, "create", new=AsyncMock(return_value=plan_response)):
        result = await executor.execute(AGENT_SPEC, {"query": "hi"})

    assert result.status == "completed"
    assert result.output["result"] == "hello"


@pytest.mark.asyncio
async def test_execute_code_path():
    executor = AgentExecutorAgent()
    plan_response = MagicMock()
    plan_response.choices[0].message.content = (
        '{"action": "EXECUTE_CODE", "code": "print(\'test output\')", "credential_keys": []}'
    )
    synth_response = MagicMock()
    synth_response.choices[0].message.content = '{"result": "test output"}'

    responses = [plan_response, synth_response]
    call_count = 0

    async def mock_create(**kwargs):
        nonlocal call_count
        r = responses[call_count]
        call_count += 1
        return r

    with patch.object(executor.client.chat.completions, "create", new=mock_create):
        result = await executor.execute(AGENT_SPEC, {})

    assert result.status == "completed"
    assert result.output["result"] == "test output"
    assert "_code" in result.output


@pytest.mark.asyncio
async def test_code_event_callback_called():
    executor = AgentExecutorAgent()
    plan_response = MagicMock()
    plan_response.choices[0].message.content = '{"action": "NO_CODE_NEEDED", "output": {"result": "x"}}'
    phases = []

    async def on_event(agent_id, phase, preview):
        phases.append(phase)

    with patch.object(executor.client.chat.completions, "create", new=AsyncMock(return_value=plan_response)):
        await executor.execute(AGENT_SPEC, {}, on_code_event=on_event)

    assert "planning" in phases
    assert "fallback" in phases
```

- [ ] **Step 3: Run tests**

```
cd backend && python -m pytest tests/test_agent_executor.py -v
```

Expected: 3 PASSED

- [ ] **Step 4: Commit**

```
git add backend/app/agents/agent_executor.py backend/tests/test_agent_executor.py
git commit -m "feat: PLAN→EXEC→SYNTH executor loop with code generation and subprocess execution"
```

---

## Task 3: Emit CODE_STATUS Events from ws_run.py

**Files:**
- Modify: `backend/app/api/ws_run.py`

The WS run handler needs to forward `on_code_event` callbacks as `CODE_STATUS` WebSocket events.

- [ ] **Step 1: Update `ws_run_handler` in `ws_run.py`**

Replace the `executor.execute(agent_spec, context)` call block (lines 88–90) with:

```python
        for agent_spec in ordered_agents:
            await send(
                "AGENT_STARTED",
                {
                    "agent_id": agent_spec["agent_id"],
                    "agent_name": agent_spec["agent_name"],
                },
            )

            async def _on_code_event(agent_id: str, phase: str, code_preview: str | None):
                await send(
                    "CODE_STATUS",
                    {
                        "agent_id": agent_id,
                        "phase": phase,
                        "elapsed_ms": int(time.time() * 1000) - start_ms,
                        "code_preview": code_preview,
                    },
                )

            result = await executor.execute(agent_spec, context, on_code_event=_on_code_event)
            results.append(result)
            context.update(result.output)
```

Also add `import time` at the top of the file and a `start_ms = int(time.time() * 1000)` line just before the `for agent_spec` loop.

The full updated `ws_run.py`:

```python
import logging
import time
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.agents.agent_executor import AgentExecutorAgent
from app.models.pipeline import PipelineORM
from app.models.run import RunORM
from app.config import settings

logger = logging.getLogger(__name__)


def _topological_order(agents: list[dict]) -> list[dict]:
    """Return agents in dependency order (simple topological sort)."""
    agent_map = {agent["agent_id"]: agent for agent in agents}
    visited: set[str] = set()
    order: list[dict] = []

    def visit(agent_id: str):
        if agent_id in visited:
            return
        visited.add(agent_id)
        for dep in agent_map.get(agent_id, {}).get("depends_on", []):
            if dep in agent_map:
                visit(dep)
        order.append(agent_map[agent_id])

    for agent in agents:
        visit(agent["agent_id"])
    return order


async def ws_run_handler(websocket: WebSocket, run_id: str):
    await websocket.accept()

    db: Session = SessionLocal()
    try:
        run = db.query(RunORM).filter(RunORM.id == run_id).first()
        if not run:
            await websocket.send_json({"type": "ERROR", "message": "Run not found"})
            await websocket.close()
            return

        pipeline = db.query(PipelineORM).filter(PipelineORM.id == run.pipeline_id).first()
        if not pipeline:
            await websocket.send_json({"type": "ERROR", "message": "Pipeline not found"})
            await websocket.close()
            return

        async def send(event_type: str, data: dict):
            await websocket.send_json({"type": event_type, "run_id": run_id, **data})

        if not settings.active_api_key:
            await send("ERROR", {"message": "No API key configured. Add GEMINI_API_KEY to backend/.env"})
            await websocket.close()
            return

        run.status = "running"
        db.commit()

        await send(
            "RUN_STARTED",
            {
                "pipeline_id": run.pipeline_id,
                "objective": pipeline.objective,
                "inputs": run.inputs,
            },
        )

        blueprint = pipeline.blueprint or {}
        agents = blueprint.get("agents", [])
        ordered_agents = _topological_order(agents)

        executor = AgentExecutorAgent()
        results = []
        context: dict = dict(run.inputs or {})
        start_ms = int(time.time() * 1000)

        for agent_spec in ordered_agents:
            await send(
                "AGENT_STARTED",
                {
                    "agent_id": agent_spec["agent_id"],
                    "agent_name": agent_spec["agent_name"],
                },
            )

            async def _on_code_event(agent_id: str, phase: str, code_preview: str | None):
                await send(
                    "CODE_STATUS",
                    {
                        "agent_id": agent_id,
                        "phase": phase,
                        "elapsed_ms": int(time.time() * 1000) - start_ms,
                        "code_preview": code_preview,
                    },
                )

            result = await executor.execute(agent_spec, context, on_code_event=_on_code_event)
            results.append(result)
            context.update(result.output)

            await send(
                "AGENT_RESULT",
                {
                    "agent_id": result.agent_id,
                    "agent_name": result.agent_name,
                    "status": result.status,
                    "output": result.output,
                    "error": result.error,
                    "duration_ms": result.duration_ms,
                },
            )

        failed = [result for result in results if result.status == "failed"]
        final_status = "failed" if failed else "completed"

        run.status = final_status
        run.results = [result.model_dump() for result in results]
        run.completed_at = datetime.now(timezone.utc)
        db.commit()

        await send(
            "RUN_COMPLETE",
            {
                "status": final_status,
                "total_agents": len(ordered_agents),
                "completed": len([result for result in results if result.status == "completed"]),
                "failed": len(failed),
                "results": [result.model_dump() for result in results],
            },
        )

    except WebSocketDisconnect:
        logger.info("Run WS disconnected: %s", run_id)
    except Exception as exc:
        logger.error("Run WS error for run %s: %s", run_id, exc, exc_info=True)
        try:
            await websocket.send_json({"type": "ERROR", "message": str(exc)})
        except Exception:
            pass
    finally:
        db.close()
```

- [ ] **Step 2: Commit**

```
git add backend/app/api/ws_run.py
git commit -m "feat: emit CODE_STATUS WS events for each executor phase"
```

---

## Task 4: Add trigger_config to AgentMaster prompt

**Files:**
- Modify: `backend/app/prompts/master.py`

- [ ] **Step 1: Add `trigger_config` to the OUTPUT FORMAT section**

In `master.py`, find the `AGENT_MASTER_SYSTEM_PROMPT` string. Inside the output format JSON (after `"library_patterns_found"`), add the `trigger_config` field.

Replace this part of the prompt:
```
  "library_patterns_found": []
}
```
With:
```
  "library_patterns_found": [],
  "trigger_config": {
    "mode": "manual | scheduled | webhook",
    "interval_minutes": null,
    "description": "One sentence: why this trigger mode was chosen"
  }
}
```

Also add this paragraph to the `## YOUR ROLE` section (after item 5):
```
6. Decide the trigger_config: how this pipeline should be activated
   - "manual": one-off analysis, on-demand tasks, interactive pipelines
   - "scheduled": continuous monitoring, periodic checks, recurring jobs (set interval_minutes)
   - "webhook": event-driven reactions to external pushes (GitHub webhooks, GCP alerts, etc.)
```

The full updated `AGENT_MASTER_SYSTEM_PROMPT` OUTPUT FORMAT block:

```python
## OUTPUT FORMAT (in-scope objectives only)
Respond with a JSON object ONLY — no markdown, no prose:
{
  "out_of_scope": false,
  "objective_summary": "...",
  "domain": "software_development | observability | both",
  "required_inputs": [{"name": "...", "type": "string|url|credential|file|selection", "description": "...", "required": true}],
  "agents": [
    {
      "agent_id": "agent_001",
      "agent_name": "DescriptiveName",
      "description": "Single sentence: what ONE action this agent performs",
      "input_schema": {"field": {"type": "string", "required": true, "description": "..."}},
      "output_schema": {"field": {"type": "string", "description": "..."}},
      "error_schema": {"error_type": {"description": "...", "recovery": "..."}},
      "depends_on": [],
      "timeout_seconds": 60
    }
  ],
  "edges": [
    {"from": "agent_001", "to": "agent_002", "payload_description": "..."}
  ],
  "library_patterns_found": [],
  "trigger_config": {
    "mode": "manual",
    "interval_minutes": null,
    "description": "One sentence: why this trigger mode was chosen"
  }
}
```

- [ ] **Step 2: Commit**

```
git add backend/app/prompts/master.py
git commit -m "feat: AgentMaster design prompt now outputs trigger_config"
```

---

## Task 5: Add default_inputs column to PipelineORM

**Files:**
- Modify: `backend/app/models/pipeline.py`
- Modify: `backend/app/api/routes/pipelines.py`

- [ ] **Step 1: Add `default_inputs` to `PipelineORM` and `Pipeline` model**

In `pipeline.py`, add the column to `PipelineORM` and the field to `Pipeline`:

```python
# In PipelineORM class, add after `blueprint` column:
    default_inputs = Column(JSON, default=dict)

# In Pipeline Pydantic model, add after `blueprint` field:
    default_inputs: dict[str, str] = Field(default_factory=dict)
    trigger_config: dict | None = None
```

Also update `_orm_to_pipeline` in `pipelines.py`:
```python
def _orm_to_pipeline(row: PipelineORM) -> Pipeline:
    blueprint = row.blueprint or {}
    return Pipeline(
        id=row.id,
        objective=row.objective,
        name=row.name,
        input_schema=row.input_schema or [],
        blueprint=blueprint,
        default_inputs=row.default_inputs or {},
        trigger_config=blueprint.get("trigger_config"),
        created_at=str(row.created_at) if row.created_at else None,
        updated_at=str(row.updated_at) if row.updated_at else None,
    )
```

And update `_orm_to_summary` to include `trigger_config`:
```python
def _orm_to_summary(row: PipelineORM) -> PipelineSummary:
    blueprint = row.blueprint or {}
    agent_count = len(blueprint.get("agents", []))
    trigger_config = blueprint.get("trigger_config")
    return PipelineSummary(
        id=row.id,
        objective=row.objective,
        name=row.name,
        agent_count=agent_count,
        trigger_config=trigger_config,
        created_at=str(row.created_at) if row.created_at else None,
    )
```

Also update `PipelineSummary` in `models/pipeline.py`:
```python
class PipelineSummary(BaseModel):
    id: str
    objective: str
    name: str
    agent_count: int = 0
    trigger_config: dict | None = None
    created_at: str | None = None
```

- [ ] **Step 2: Add PATCH /{pipeline_id}/credentials endpoint to `pipelines.py`**

```python
class UpdateCredentialsRequest(BaseModel):
    default_inputs: dict[str, str]


@router.patch("/{pipeline_id}/credentials", response_model=Pipeline)
def update_credentials(pipeline_id: str, req: UpdateCredentialsRequest, db: Session = Depends(get_db)):
    row = db.query(PipelineORM).filter(PipelineORM.id == pipeline_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    row.default_inputs = req.default_inputs
    db.commit()
    db.refresh(row)
    backup_to_gcs()
    return _orm_to_pipeline(row)
```

- [ ] **Step 3: Commit**

```
git add backend/app/models/pipeline.py backend/app/api/routes/pipelines.py
git commit -m "feat: add default_inputs column and credentials PATCH endpoint to pipelines"
```

---

## Task 6: headless_run.py — Non-WS Pipeline Execution for Scheduler

**Files:**
- Create: `backend/app/agents/headless_run.py`

The scheduler needs to run pipelines without a WebSocket connection.

- [ ] **Step 1: Create `headless_run.py`**

```python
# backend/app/agents/headless_run.py
"""Non-WebSocket pipeline execution for scheduled and webhook-triggered runs."""
import logging
from datetime import datetime, timezone

from app.db import SessionLocal
from app.agents.agent_executor import AgentExecutorAgent
from app.api.ws_run import _topological_order
from app.models.pipeline import PipelineORM
from app.models.run import RunORM
from app.gcs_backup import backup_to_gcs

logger = logging.getLogger(__name__)


async def execute_run_headless(run_id: str) -> None:
    """Execute a pipeline run without WebSocket — updates DB only."""
    db = SessionLocal()
    try:
        run = db.query(RunORM).filter(RunORM.id == run_id).first()
        if not run:
            logger.error("Headless run: run %s not found", run_id)
            return

        pipeline = db.query(PipelineORM).filter(PipelineORM.id == run.pipeline_id).first()
        if not pipeline:
            logger.error("Headless run: pipeline %s not found", run.pipeline_id)
            run.status = "failed"
            db.commit()
            return

        run.status = "running"
        db.commit()

        blueprint = pipeline.blueprint or {}
        agents = blueprint.get("agents", [])
        ordered_agents = _topological_order(agents)

        executor = AgentExecutorAgent()
        results = []
        context: dict = dict(run.inputs or {})

        for agent_spec in ordered_agents:
            result = await executor.execute(agent_spec, context)
            results.append(result)
            context.update(result.output)
            logger.info("Headless run %s: agent %s → %s", run_id, agent_spec["agent_id"], result.status)

        failed = [r for r in results if r.status == "failed"]
        final_status = "failed" if failed else "completed"

        run.status = final_status
        run.results = [r.model_dump() for r in results]
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        backup_to_gcs()

        logger.info("Headless run %s complete: %s (%d agents)", run_id, final_status, len(results))

    except Exception as exc:
        logger.error("Headless run %s failed: %s", run_id, exc, exc_info=True)
        try:
            run.status = "failed"
            db.commit()
        except Exception:
            pass
    finally:
        db.close()
```

- [ ] **Step 2: Commit**

```
git add backend/app/agents/headless_run.py
git commit -m "feat: headless pipeline execution for scheduler and webhook triggers"
```

---

## Task 7: scheduler.py + main.py Integration

**Files:**
- Create: `backend/app/scheduler.py`
- Modify: `backend/app/main.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Create `scheduler.py`**

```python
# backend/app/scheduler.py
import asyncio
import logging
import uuid
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler()


def get_scheduler() -> AsyncIOScheduler:
    return _scheduler


async def _run_pipeline_scheduled(pipeline_id: str) -> None:
    """Create a run record and execute headlessly for a scheduled pipeline."""
    from app.db import SessionLocal
    from app.models.pipeline import PipelineORM
    from app.models.run import RunORM
    from app.agents.headless_run import execute_run_headless

    db = SessionLocal()
    try:
        pipeline = db.query(PipelineORM).filter(PipelineORM.id == pipeline_id).first()
        if not pipeline:
            logger.warning("Scheduled pipeline %s not found — removing job", pipeline_id)
            unregister_pipeline_schedule(pipeline_id)
            return

        run_id = str(uuid.uuid4())
        run = RunORM(
            id=run_id,
            pipeline_id=pipeline_id,
            status="pending",
            inputs=pipeline.default_inputs or {},
            triggered_by="schedule",
        )
        db.add(run)
        db.commit()
        logger.info("Scheduler created run %s for pipeline %s", run_id, pipeline_id)
    finally:
        db.close()

    await execute_run_headless(run_id)


def register_pipeline_schedule(pipeline_id: str, interval_minutes: int) -> None:
    job_id = f"pipeline_{pipeline_id}"
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)
    _scheduler.add_job(
        _run_pipeline_scheduled,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id=job_id,
        args=[pipeline_id],
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    logger.info("Registered schedule: pipeline %s every %d min", pipeline_id, interval_minutes)


def unregister_pipeline_schedule(pipeline_id: str) -> None:
    job_id = f"pipeline_{pipeline_id}"
    job = _scheduler.get_job(job_id)
    if job:
        _scheduler.remove_job(job_id)
        logger.info("Unregistered schedule for pipeline %s", pipeline_id)


def load_all_schedules() -> None:
    """Called on startup — register all pipelines with mode=scheduled."""
    from app.db import SessionLocal
    from app.models.pipeline import PipelineORM

    db = SessionLocal()
    try:
        pipelines = db.query(PipelineORM).all()
        count = 0
        for pipeline in pipelines:
            blueprint = pipeline.blueprint or {}
            trigger = blueprint.get("trigger_config", {})
            if trigger.get("mode") == "scheduled":
                interval = int(trigger.get("interval_minutes") or 5)
                register_pipeline_schedule(pipeline.id, interval)
                count += 1
        logger.info("Loaded %d scheduled pipelines on startup", count)
    finally:
        db.close()
```

- [ ] **Step 2: Update `main.py` lifespan to start scheduler**

Replace the `lifespan` function:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    restore_from_gcs()
    Base.metadata.create_all(bind=engine)
    # Start scheduler
    from app.scheduler import get_scheduler, load_all_schedules
    scheduler = get_scheduler()
    scheduler.start()
    load_all_schedules()
    yield
    scheduler.shutdown(wait=False)
```

Also add the webhooks router import and include at the bottom of the router section:
```python
from app.api.webhooks import router as webhooks_router
# ...
app.include_router(webhooks_router)
```

- [ ] **Step 3: Add `apscheduler` to `requirements.txt`**

Add this line:
```
apscheduler==3.10.4
```

- [ ] **Step 4: Commit**

```
git add backend/app/scheduler.py backend/app/main.py backend/requirements.txt
git commit -m "feat: APScheduler setup with auto-load of scheduled pipelines on startup"
```

---

## Task 8: webhooks.py — Webhook Trigger Endpoint

**Files:**
- Create: `backend/app/api/webhooks.py`

- [ ] **Step 1: Create `webhooks.py`**

```python
# backend/app/api/webhooks.py
import asyncio
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.pipeline import PipelineORM
from app.models.run import RunORM

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


@router.post("/{pipeline_id}")
async def trigger_webhook(
    pipeline_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Trigger a pipeline run via webhook.
    Webhook body is merged with pipeline default_inputs as runtime inputs.
    Returns run_id immediately; execution runs in background.
    """
    pipeline = db.query(PipelineORM).filter(PipelineORM.id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    # Parse body (any JSON) — merged over default inputs
    try:
        body = await request.json()
        if not isinstance(body, dict):
            body = {"payload": body}
    except Exception:
        body = {}

    # Merge: default_inputs as base, webhook body overrides
    inputs = {**(pipeline.default_inputs or {}), **{k: str(v) for k, v in body.items()}}

    run_id = str(uuid.uuid4())
    run = RunORM(
        id=run_id,
        pipeline_id=pipeline_id,
        status="pending",
        inputs=inputs,
        triggered_by="webhook",
    )
    db.add(run)
    db.commit()
    logger.info("Webhook triggered run %s for pipeline %s", run_id, pipeline_id)

    # Execute in background (non-blocking response)
    from app.agents.headless_run import execute_run_headless
    background_tasks.add_task(execute_run_headless, run_id)

    return {"run_id": run_id, "status": "started"}
```

- [ ] **Step 2: Check `RunORM` has `triggered_by` column**

Open `backend/app/models/run.py`. If `triggered_by` column is missing, add it:
```python
triggered_by = Column(String, default="manual")  # "manual" | "schedule" | "webhook"
```

- [ ] **Step 3: Commit**

```
git add backend/app/api/webhooks.py backend/app/models/run.py
git commit -m "feat: webhook endpoint to trigger pipeline runs externally"
```

---

## Task 9: Update requirements.txt and Dockerfile

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `Dockerfile`

- [ ] **Step 1: Add all new packages to `requirements.txt`**

Add these lines (they may already have `google-cloud-storage`; keep it):
```
boto3==1.34.131
google-cloud-logging==3.10.0
google-cloud-monitoring==2.21.0
PyGithub==2.3.0
kubernetes==30.1.0
apscheduler==3.10.4
```

- [ ] **Step 2: Verify Dockerfile needs no changes**

The Dockerfile already runs `pip install -r requirements.txt`. No changes needed — new packages install automatically on next build.

- [ ] **Step 3: Commit**

```
git add backend/requirements.txt
git commit -m "chore: add boto3, google-cloud-logging, PyGithub, kubernetes, apscheduler to requirements"
```

---

## Task 10: Frontend — Types, RunStore, useRunWS for CODE_STATUS

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/store/runStore.ts`
- Modify: `frontend/src/hooks/useRunWS.ts`

- [ ] **Step 1: Add `CODE_STATUS` to `RunWSEvent` and add `TriggerConfig` type in `types/index.ts`**

Add to `RunWSEvent` union (after the `RUN_COMPLETE` line):
```typescript
  | { type: "CODE_STATUS"; run_id: string; agent_id: string; phase: "planning" | "executing" | "synthesising" | "fallback"; elapsed_ms: number; code_preview: string | null }
```

Add `TriggerConfig` interface before `InputField`:
```typescript
export interface TriggerConfig {
  mode: "manual" | "scheduled" | "webhook";
  interval_minutes: number | null;
  description: string;
}
```

Update `PipelineSummary` to include `trigger_config`:
```typescript
export interface PipelineSummary {
  id: string;
  objective: string;
  name: string;
  agent_count: number;
  trigger_config: TriggerConfig | null;
  created_at: string | null;
}
```

Update `Pipeline` to include `default_inputs` and `trigger_config`:
```typescript
export interface Pipeline {
  id: string;
  objective: string;
  name: string;
  input_schema: InputField[];
  blueprint: Record<string, unknown>;
  default_inputs: Record<string, string>;
  trigger_config: TriggerConfig | null;
  created_at: string | null;
  updated_at: string | null;
}
```

- [ ] **Step 2: Add `CodeStatus` type and `codeStatus` to `RunStore` in `runStore.ts`**

Add `CodeStatus` interface above the `RunStore` interface:
```typescript
export interface CodeStatus {
  phase: "planning" | "executing" | "synthesising" | "fallback";
  elapsed_ms: number;
  code_preview: string | null;
}
```

Update `RunStore` interface — add after `isComplete`:
```typescript
  codeStatus: Record<string, CodeStatus>;
  setCodeStatus: (agentId: string, status: CodeStatus) => void;
```

Update `useRunStore` create — add initial value and setter:
```typescript
  codeStatus: {},
  setCodeStatus: (agentId, status) =>
    set((s) => ({ codeStatus: { ...s.codeStatus, [agentId]: status } })),
```

Also update `reset`:
```typescript
  reset: () =>
    set({ run: null, activeResults: {}, runEvents: [], isConnected: false, isComplete: false, codeStatus: {} }),
```

- [ ] **Step 3: Handle `CODE_STATUS` in `useRunWS.ts`**

Add to the `switch` block inside `socket.onmessage`:
```typescript
        case "CODE_STATUS":
          store.setCodeStatus(event.agent_id, {
            phase: event.phase,
            elapsed_ms: event.elapsed_ms,
            code_preview: event.code_preview,
          });
          break;
```

- [ ] **Step 4: Commit**

```
git add frontend/src/types/index.ts frontend/src/store/runStore.ts frontend/src/hooks/useRunWS.ts
git commit -m "feat: CODE_STATUS WS event type, codeStatus in RunStore, useRunWS handler"
```

---

## Task 11: Frontend — Agent Cards with Code/Phase Indicators

**Files:**
- Modify: `frontend/src/components/AgentListColumn.tsx`

The `RunAgentList` section needs to show execution phase and expandable code/stdout.

- [ ] **Step 1: Update `AgentListColumn.tsx` — add `CodePhaseIndicator` component and update run card**

Find the `RunAgentList` component (search for `export function RunAgentList`). Add these helpers just before it:

```typescript
import { useState } from "react";
import type { CodeStatus } from "../store/runStore";
import { useRunStore } from "../store/runStore";

function phaseLabel(phase: CodeStatus["phase"]): string {
  if (phase === "planning") return "⚙️ Writing code…";
  if (phase === "executing") return "⚡ Executing…";
  if (phase === "synthesising") return "🔁 Synthesising…";
  return "💭 Reasoning…";
}

function CodePhaseIndicator({ agentId }: { agentId: string }) {
  const codeStatus = useRunStore((s) => s.codeStatus[agentId]);
  if (!codeStatus) return null;
  return (
    <div className="text-xs text-amber-400 font-mono mt-1 animate-pulse">
      {phaseLabel(codeStatus.phase)}
      {codeStatus.elapsed_ms > 0 && (
        <span className="text-gray-600 ml-2">{(codeStatus.elapsed_ms / 1000).toFixed(1)}s</span>
      )}
    </div>
  );
}

function CodePreviewExpander({ output }: { output: Record<string, unknown> }) {
  const [open, setOpen] = useState(false);
  const code = output["_code"] as string | undefined;
  const stdout = output["_stdout_preview"] as string | undefined;
  if (!code) return null;
  return (
    <div className="mt-1.5">
      <button
        className="text-xs text-gray-600 hover:text-cyan-400 font-mono underline"
        onClick={(e) => { e.stopPropagation(); setOpen((v) => !v); }}
      >
        {open ? "▲ hide code" : "▼ show code"}
      </button>
      {open && (
        <div className="mt-1 space-y-1">
          <pre className="text-xs bg-[#0d1117] border border-gray-800 rounded p-2 text-cyan-300 overflow-x-auto font-mono max-h-40">
            {code}
          </pre>
          {stdout && (
            <pre className="text-xs bg-[#0d1117] border border-gray-800 rounded p-2 text-green-300 overflow-x-auto font-mono max-h-24">
              {stdout}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
```

Then in the run agent card JSX (where `outputPreview` is shown), add `<CodePhaseIndicator>` for running agents and `<CodePreviewExpander>` for completed agents:

Inside the card body (after the agent name/status line), add:
```tsx
{/* Show execution phase while running */}
{result?.status !== "completed" && result?.status !== "failed" && (
  <CodePhaseIndicator agentId={agent.agent_id} />
)}
{/* Show code expander when complete */}
{result?.status === "completed" && result.output && (
  <CodePreviewExpander output={result.output} />
)}
```

- [ ] **Step 2: Commit**

```
git add frontend/src/components/AgentListColumn.tsx
git commit -m "feat: agent run cards show code execution phase and expandable code/stdout"
```

---

## Task 12: Frontend — PipelinesPage Trigger Badge + Webhook URL + Credentials Button

**Files:**
- Modify: `frontend/src/pages/PipelinesPage.tsx`

- [ ] **Step 1: Add `TriggerBadge` component and update pipeline card in `PipelinesPage.tsx`**

Add `TriggerBadge` near `StatusBadge`:
```typescript
import type { TriggerConfig } from "../types";

function TriggerBadge({ trigger }: { trigger: TriggerConfig | null }) {
  if (!trigger || trigger.mode === "manual") return null;
  if (trigger.mode === "scheduled") {
    return (
      <span className="text-xs px-2 py-0.5 rounded-full bg-purple-900/50 border border-purple-700/50 text-purple-300 font-mono">
        ⏱ Every {trigger.interval_minutes}m
      </span>
    );
  }
  return (
    <span className="text-xs px-2 py-0.5 rounded-full bg-orange-900/50 border border-orange-700/50 text-orange-300 font-mono">
      📡 Webhook
    </span>
  );
}
```

Add `handleCopyWebhook` and `setCredentialsPipelineId` state to `PipelinesPage`:
```typescript
const [credentialsPipelineId, setCredentialsPipelineId] = useState<string | null>(null);

const handleCopyWebhook = (e: React.MouseEvent, id: string) => {
  e.stopPropagation();
  const url = `${window.location.origin}/api/webhooks/${id}`;
  navigator.clipboard.writeText(url).then(() => alert("Webhook URL copied!"));
};
```

In the pipeline card JSX, inside the `flex items-center gap-3 mb-1 flex-wrap` div, add after `<StatusBadge>`:
```tsx
<TriggerBadge trigger={p.trigger_config} />
```

In the action buttons area (after the ✏ Design button), add:
```tsx
<button
  className="opacity-0 group-hover:opacity-100 bg-[#161b22] hover:bg-orange-900/40 border border-gray-700 hover:border-orange-700 text-gray-400 hover:text-orange-300 text-xs font-bold px-3 py-1.5 rounded-lg font-mono transition-all"
  onClick={(e) => handleCopyWebhook(e, p.id)}
  title="Copy webhook URL"
>
  📡
</button>
<button
  className="opacity-0 group-hover:opacity-100 bg-[#161b22] hover:bg-gray-700 border border-gray-700 text-gray-400 hover:text-white text-xs font-bold px-3 py-1.5 rounded-lg font-mono transition-all"
  onClick={(e) => { e.stopPropagation(); setCredentialsPipelineId(p.id); }}
  title="Manage credentials"
>
  🔑
</button>
```

Add the `CredentialsPanel` at the bottom of the return JSX (before closing `</div>`):
```tsx
{credentialsPipelineId && (
  <CredentialsPanel
    pipelineId={credentialsPipelineId}
    onClose={() => setCredentialsPipelineId(null)}
  />
)}
```

Add import at top:
```typescript
import { CredentialsPanel } from "../components/CredentialsPanel";
```

- [ ] **Step 2: Commit**

```
git add frontend/src/pages/PipelinesPage.tsx
git commit -m "feat: PipelinesPage trigger badge, webhook URL copy, credentials button"
```

---

## Task 13: Frontend — CredentialsPanel Component

**Files:**
- Create: `frontend/src/components/CredentialsPanel.tsx`

- [ ] **Step 1: Create `CredentialsPanel.tsx`**

```tsx
// frontend/src/components/CredentialsPanel.tsx
import { useState, useEffect } from "react";
import axios from "axios";
import { apiUrl } from "../api/client";

interface Props {
  pipelineId: string;
  onClose: () => void;
}

interface KVRow {
  key: string;
  value: string;
  masked: boolean;
}

export function CredentialsPanel({ pipelineId, onClose }: Props) {
  const [rows, setRows] = useState<KVRow[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    // Load existing default_inputs
    axios.get(apiUrl(`/api/pipelines/${pipelineId}`)).then(({ data }) => {
      const inputs: Record<string, string> = data.default_inputs || {};
      setRows(
        Object.entries(inputs).map(([key, value]) => ({ key, value, masked: true }))
      );
    });
  }, [pipelineId]);

  const addRow = () => setRows((r) => [...r, { key: "", value: "", masked: false }]);

  const removeRow = (i: number) => setRows((r) => r.filter((_, idx) => idx !== i));

  const updateRow = (i: number, field: "key" | "value", val: string) =>
    setRows((r) => r.map((row, idx) => (idx === i ? { ...row, [field]: val } : row)));

  const toggleMask = (i: number) =>
    setRows((r) => r.map((row, idx) => (idx === i ? { ...row, masked: !row.masked } : row)));

  const handleSave = async () => {
    setSaving(true);
    const default_inputs: Record<string, string> = {};
    for (const row of rows) {
      if (row.key.trim()) default_inputs[row.key.trim()] = row.value;
    }
    try {
      await axios.patch(apiUrl(`/api/pipelines/${pipelineId}/credentials`), { default_inputs });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      alert("Failed to save credentials.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-end">
      <div className="bg-[#0d1117] border-l border-gray-800 w-full max-w-md h-full flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800">
          <div>
            <h2 className="text-white font-bold font-mono text-sm">Pipeline Credentials</h2>
            <p className="text-gray-600 text-xs font-mono mt-0.5">
              Stored for scheduled & webhook runs. Injected as env vars.
            </p>
          </div>
          <button
            className="text-gray-500 hover:text-white font-mono text-lg"
            onClick={onClose}
          >
            ✕
          </button>
        </div>

        {/* Rows */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-2">
          {rows.map((row, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                className="flex-1 bg-gray-900 border border-gray-700 text-white text-xs px-3 py-2 rounded font-mono focus:outline-none focus:border-cyan-600"
                placeholder="KEY_NAME"
                value={row.key}
                onChange={(e) => updateRow(i, "key", e.target.value)}
              />
              <div className="relative flex-1">
                <input
                  className="w-full bg-gray-900 border border-gray-700 text-white text-xs px-3 py-2 rounded font-mono focus:outline-none focus:border-cyan-600 pr-8"
                  placeholder="value"
                  type={row.masked ? "password" : "text"}
                  value={row.value}
                  onChange={(e) => updateRow(i, "value", e.target.value)}
                />
                <button
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-600 hover:text-gray-300 text-xs"
                  onClick={() => toggleMask(i)}
                  title={row.masked ? "Show" : "Hide"}
                >
                  {row.masked ? "👁" : "🙈"}
                </button>
              </div>
              <button
                className="text-gray-600 hover:text-red-400 text-xs font-mono"
                onClick={() => removeRow(i)}
              >
                ✕
              </button>
            </div>
          ))}
          <button
            className="text-cyan-600 hover:text-cyan-400 text-xs font-mono mt-2"
            onClick={addRow}
          >
            + Add credential
          </button>
        </div>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-gray-800 flex items-center justify-between">
          <p className="text-gray-700 text-xs font-mono">
            Values encrypted at rest via GCS
          </p>
          <button
            className="bg-cyan-700 hover:bg-cyan-600 disabled:bg-gray-700 disabled:text-gray-600 text-white font-bold px-5 py-2 rounded-lg text-sm font-mono transition-colors"
            onClick={handleSave}
            disabled={saving}
          >
            {saved ? "✓ Saved" : saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```
git add frontend/src/components/CredentialsPanel.tsx
git commit -m "feat: CredentialsPanel with masked key-value editor and save to API"
```

---

## Task 14: Frontend — DesignPage trigger_config Chip

**Files:**
- Modify: `frontend/src/pages/DesignPage.tsx`

- [ ] **Step 1: Find and update the context bar in DesignPage**

In `DesignPage.tsx`, find where `isComplete` and `blueprint` are used in the context bar. The blueprint is available from the design store — `useDesignStore((s) => s.dag)` and the full blueprint is saved in the pipeline after design.

After design completes, `pipeline.blueprint.trigger_config` is available. Read it from the loaded pipeline state:

Find the `pipeline` state variable (loaded from API on mount). After design completes, add a trigger_config chip to the context bar area.

Locate the context bar section (search for `isComplete` in the JSX). Add this chip after the pipeline name/objective display, visible only when `isComplete`:

```tsx
{isComplete && pipeline?.blueprint?.trigger_config && (() => {
  const tc = pipeline.blueprint.trigger_config as { mode: string; interval_minutes?: number; description?: string };
  return (
    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-purple-900/30 border border-purple-700/30 text-purple-300 text-xs font-mono">
      {tc.mode === "scheduled" && `⏱ Auto-runs every ${tc.interval_minutes ?? 5}m`}
      {tc.mode === "webhook" && "📡 Webhook-triggered"}
      {tc.mode === "manual" && "▶ Manual run"}
    </div>
  );
})()}
```

Also, after design completes and pipeline blueprint is saved, re-register schedules if trigger_config changed. In the design completion handler (where the blueprint is saved to DB), call:

```typescript
// After blueprint is saved — update schedule if needed
if (triggerConfig?.mode === "scheduled" && triggerConfig.interval_minutes) {
  // Schedule is auto-loaded on next server restart; no client-side action needed
  // Server handles it via load_all_schedules on startup
}
```

Note: schedule auto-registration on blueprint save is handled server-side in the next step.

- [ ] **Step 2: Register schedule when blueprint is saved in ws_design.py**

Open `backend/app/api/ws_design.py`. Find where `pipeline.blueprint = blueprint` is set and `db.commit()` is called. After the commit, add:

```python
# Re-register schedule if trigger_config changed
trigger = blueprint.get("trigger_config", {})
if trigger.get("mode") == "scheduled":
    from app.scheduler import register_pipeline_schedule
    interval = int(trigger.get("interval_minutes") or 5)
    register_pipeline_schedule(pipeline.id, interval)
elif trigger.get("mode") != "scheduled":
    from app.scheduler import unregister_pipeline_schedule
    unregister_pipeline_schedule(pipeline.id)
```

- [ ] **Step 3: Commit**

```
git add frontend/src/pages/DesignPage.tsx backend/app/api/ws_design.py
git commit -m "feat: show trigger_config chip in DesignPage; auto-register schedule on blueprint save"
```

---

## Task 15: Deploy + Verify

**Files:**
- Run: `.\deploy.ps1`

- [ ] **Step 1: Run deploy script**

```powershell
cd C:\Users\schinta\AgentMaster
.\deploy.ps1
```

Expected: Cloud Run revision deployed successfully

- [ ] **Step 2: Smoke test — verify executor runs real code**

Open the live URL, create a new pipeline with objective:
> "Fetch the current UTC time and return it"

Design it → Run it. The executor should write Python code `import datetime; print(...)` and return real time, not a simulated value.

Check Run page: agent card should show `⚡ Executing…` during execution and a `▼ show code` expander after completion.

- [ ] **Step 3: Smoke test — verify trigger_config in blueprint**

Design a pipeline with objective:
> "Monitor GCP Cloud Logging for ERROR severity events every 5 minutes"

After design, the context bar chip should show `⏱ Auto-runs every 5m`.

- [ ] **Step 4: Smoke test — credentials panel**

On PipelinesPage, hover over any pipeline card. Click 🔑. Add key `GITHUB_TOKEN` with value `test`. Save. Reload. Check the key persists (value masked).

- [ ] **Step 5: Smoke test — webhook copy**

Hover a pipeline card. Click 📡. Verify the copied URL is `https://agentmaster-xxx.run.app/api/webhooks/{id}`.

- [ ] **Step 6: Final commit**

```
git add .
git commit -m "chore: post-deploy verification complete — real execution engine v1"
```
