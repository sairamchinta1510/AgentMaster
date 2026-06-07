# Real Execution Engine — Design Spec
**Date:** 2026-06-07  
**Status:** Approved

---

## Problem

AgentMaster currently simulates execution: every agent run is an LLM call that *pretends* to fetch logs, call APIs, or scale infrastructure. No real data is ever retrieved. This makes pipelines like LogErrorParser and HW-ScaleUp unusable for production monitoring and automation.

---

## Goal

Every agent in any pipeline should be able to perform **real work** in the world — call APIs, read repos, query log systems, trigger infrastructure changes — without any pre-registered tools or hardcoded integrations. AgentMaster decides autonomously how to execute each agent based on its design-time spec.

---

## Architecture Overview

Three independent additions:

1. **Code-Generation Executor** — agents write and run real Python code  
2. **Trigger System** — the design agent decides how each pipeline should be activated (scheduled / webhook / manual)  
3. **UI additions** — surface code execution, trigger config, and credentials in the UI

---

## 1. Code-Generation Executor

### Execution Flow

```
For each agent in a pipeline run:

  PLAN phase:
    LLM receives:
      - agent_name, description
      - input_schema, output_schema
      - context_inputs (runtime values including credentials)
    LLM writes Python code to accomplish the task.
    Code reads credentials from os.environ (never hardcoded).

  EXEC phase:
    AgentMaster writes code to a temp file.
    Runs: python <tempfile> with credentials injected as env vars.
    Timeout: 60 seconds.
    Captures: stdout (success output), stderr (error log).

  SYNTH phase:
    stdout + stderr fed back to LLM.
    LLM synthesises final JSON object matching output_schema.
    AgentResult returned as normal (status, output, duration_ms).

  FALLBACK:
    If LLM determines no real API calls are needed (pure reasoning/transformation),
    it returns "NO_CODE_NEEDED" and execution proceeds as today (direct JSON output).
```

### Code Contract

The LLM is instructed to write code that:
- Reads credentials exclusively via `os.environ["KEY_NAME"]`
- Prints a JSON-serialisable result to stdout on the last line
- Handles its own errors (prints to stderr, exits 0)
- Installs no packages at runtime (pre-installed packages only)

### Pre-installed Packages

Added to `requirements.txt` and Docker image:
- `boto3` — AWS CloudWatch, S3, EC2, etc.
- `google-cloud-logging` — GCP Cloud Logging
- `google-cloud-monitoring` — GCP Metrics / alerting
- `PyGithub` — GitHub API (repos, issues, commits, files)
- `kubernetes` — Kubernetes API for cluster operations
- `requests` — general HTTP (httpx already present)

These cover the known use cases (log monitoring, GitHub, infra scaling) without restricting the LLM to only these.

### Security

- Code runs inside the Cloud Run container (already network-isolated)
- Credentials passed as env vars, never written to disk
- `subprocess` timeout enforced (60s hard kill)
- Dangerous file-system operations blocked: the LLM system prompt instructs it never to write to paths outside `/tmp` and never to execute shell destructive commands (`rm -rf`, `kill`, etc.)
- stdout size capped at 50 KB before being sent back to LLM

### New Backend Files

```
backend/app/agents/
  code_executor.py          ← subprocess runner (new)
  agent_executor.py         ← updated: orchestrates PLAN→EXEC→SYNTH
```

---

## 2. Trigger System

### Design-Time: trigger_config in Blueprint

The AgentMasterAgent (design agent) already produces a `blueprint` JSON. It is extended to include a `trigger_config` field:

```json
"trigger_config": {
  "mode": "scheduled",
  "interval_minutes": 5,
  "description": "Polls GCP Cloud Logging every 5 minutes for ERROR severity events"
}
```

Possible modes:

| Mode | Meaning |
|---|---|
| `manual` | User clicks Run (current default for all pipelines) |
| `scheduled` | Backend runs pipeline on interval; `interval_minutes` required |
| `webhook` | Backend exposes POST endpoint; external system triggers |

**AgentMaster decides** which mode is appropriate based on the pipeline's objective. A log monitoring pipeline → `scheduled`. A "react to GitHub push" pipeline → `webhook`. A one-off analysis → `manual`. The design agent is prompted to always emit `trigger_config`.

### Runtime: Scheduled Execution

- `APScheduler` (AsyncIOScheduler) added to FastAPI lifespan
- On startup, all pipelines with `trigger_config.mode == "scheduled"` are loaded and scheduled
- When a scheduled run fires, it creates a new `RunORM` with `triggered_by: "schedule"` and executes using stored default credentials
- Schedule is re-registered whenever a pipeline is saved/updated

### Runtime: Webhook Execution

- Endpoint: `POST /api/webhooks/{pipeline_id}`
- Accepts any JSON body; body merged into default credentials as runtime inputs
- Returns `{"run_id": "..."}` immediately; execution is async
- No authentication on the endpoint in v1 (URL is the secret)
- Webhook URL shown in UI for copy

### Default Credentials Storage

For unattended runs (scheduled + webhook), pipelines store a set of default credentials:
- Stored as `pipeline.default_inputs` JSON column (encrypted at rest via GCS bucket encryption)
- Keys are credential names (e.g., `GITHUB_TOKEN`, `GCP_SERVICE_ACCOUNT_JSON`)
- Values are masked in UI (shown as `••••••`)
- User sets them once in the pipeline settings panel
- At run time, default_inputs are merged with any runtime overrides

### New Backend Files

```
backend/app/
  scheduler.py              ← APScheduler setup (new)
  api/webhooks.py           ← POST /api/webhooks/{pipeline_id} (new)
  models/pipeline.py        ← add default_inputs column (updated)
```

New package: `apscheduler==3.10.4`

---

## 3. UI Changes

### PipelinesPage — Pipeline Card

Each pipeline card gains:
- **Trigger badge**: `⏱ Every 5 min` (scheduled) / `📡 Webhook` / `▶ Manual`
- **📡 Webhook URL** copy button (visible when mode=webhook or always, for flexibility)
- **⚙️ Credentials** button → opens `CredentialsPanel` side drawer

### CredentialsPanel (new component)

- Key-value editor for default credentials
- Values masked; show/hide toggle per row
- Add / remove rows
- Save button → PATCH /api/pipelines/{id}/credentials
- Pre-populates with credential names inferred from last run's runtime inputs

### DesignPage — Context Bar

After design completes, shows trigger_config summary:
- `"AgentMaster decided: scheduled every 5 min"` in a small info chip
- User can click to override in CredentialsPanel

### RunPage — Agent Cards

During execution, each agent card shows a new execution phase line:
- `⚙️ Writing code...` (PLAN phase)
- `⚡ Executing (12s)...` (EXEC phase, live timer)
- `✅ Code complete` or `⚠️ Fallback to LLM`

Expandable section on completed cards:
- **Generated code** (syntax-highlighted, collapsed by default)
- **stdout preview** (first 5 lines)

### WebSocket: New Event Type

New WS event `CODE_STATUS` emitted during agent execution:
```json
{
  "type": "CODE_STATUS",
  "agent_id": "...",
  "phase": "planning" | "executing" | "synthesising" | "fallback",
  "elapsed_ms": 4200,
  "code_preview": "import os, httpx\ntoken = os.environ[..."
}
```

Frontend RunStore adds `codeStatus: Record<agentId, CodeStatus>`.

---

## 4. Data Flow Example: LogErrorParser Pipeline

1. User designs pipeline → AgentMasterAgent produces blueprint with `trigger_config: {mode: "scheduled", interval_minutes: 5}`
2. User sets default credentials: `GCP_SERVICE_ACCOUNT_JSON=<key>`, `GCP_PROJECT=prj-d-srdl-casas-4zrs`
3. Every 5 minutes, scheduler fires → creates Run → executes agents:
   - **RepoScanner**: LLM writes code using PyGithub → reads `cloudbuild.yaml`, `k8s/` → detects `LOG_PROJECT=prj-d-srdl-casas-4zrs`
   - **LogFetcher**: LLM writes code using `google-cloud-logging` → queries last 5 min of ERROR logs → returns log entries
   - **ErrorAnalyser**: LLM receives real log text → no code needed (`NO_CODE_NEEDED`) → analyses and classifies errors
   - **ReportBuilder**: LLM synthesises summary → optionally writes code to POST to Slack/email webhook
4. Results persisted to DB, backed up to GCS
5. RunPage shows each agent's code + real output

---

## 5. Backward Compatibility

- All existing pipelines continue to work: `trigger_config` defaults to `{mode: "manual"}` when absent
- If LLM returns `NO_CODE_NEEDED`, agent executes exactly as today
- No changes to design WS protocol, pipeline structure, or run API
- `default_inputs` column added with `ALTER TABLE` migration (nullable, no data loss)

---

## 6. Out of Scope

- Code sandboxing beyond timeout + env var controls (full container isolation is a future concern)
- Webhook authentication (v1 uses URL-as-secret)
- Retry logic for failed scheduled runs (failed runs logged; next schedule fires normally)
- Rate limiting on webhook endpoint

---

## Implementation Tasks (for writing-plans)

1. `code_executor.py` — subprocess runner with timeout, env injection, stdout cap
2. Update `agent_executor.py` — PLAN→EXEC→SYNTH loop, `NO_CODE_NEEDED` fallback
3. Update `agent_master.py` system prompt — instruct design agent to emit `trigger_config`
4. `scheduler.py` — APScheduler setup, load scheduled pipelines on startup
5. `api/webhooks.py` — webhook endpoint
6. `models/pipeline.py` — add `default_inputs` column + migration
7. Frontend `CODE_STATUS` WS event — RunStore + useRunWS
8. Frontend RunPage agent cards — code/stdout expandable section, phase indicators
9. Frontend PipelinesPage — trigger badge, webhook URL copy, Credentials button
10. Frontend `CredentialsPanel` component — key-value editor, masked values
11. Frontend DesignPage — trigger_config chip in context bar
12. Update `requirements.txt` + Dockerfile — add boto3, google-cloud-logging, google-cloud-monitoring, PyGithub, kubernetes, apscheduler
13. Deploy + verify end-to-end with LogErrorParser pipeline
