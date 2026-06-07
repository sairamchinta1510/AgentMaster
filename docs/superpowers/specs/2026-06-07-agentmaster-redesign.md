# AgentMaster — Redesign Spec
**Date:** 2026-06-07  
**Version:** 2.0  
**Status:** Approved

---

## Overview

AgentMaster v2 is a full-stack redesign of the AAGF system. The core change: **Design Time and Run Time are now distinct, separated modes** — both in the UI and the backend API.

- **Design Time**: Describe a class of work → AI automatically builds a reusable agent pipeline → save it to your Library
- **Run Time**: Pick a saved pipeline → provide required inputs → watch agents execute live

The app is deployed as two independent services: a FastAPI backend on **GCP Cloud Run** and a React frontend as a static site on **AWS S3 + CloudFront**.

---

## Guiding Principle: "Don't Make Me Think"

The UI requires zero backend knowledge from the user. Everything that can be automated is automated. The user makes two types of decisions only: (1) what to build at Design Time, (2) what inputs to provide at Run Time.

---

## App Structure & Navigation

### Views
| View | Route | Purpose |
|---|---|---|
| Shell | `/` | Sidebar always visible; empty main panel on first load |
| Design (new) | `/design/new` | Blank objective form; AI designs pipeline |
| Design (edit) | `/design/:id` | Saved pipeline loaded in Design View |
| Run | `/run/:id` | Input form + live execution dashboard for a pipeline |

### Sidebar
- Lists all saved pipelines (name + brief description)
- Each pipeline row has two action icons: **✏️ Edit/Redesign** and **▶ Run**
- `+ New Pipeline` button at the top
- Sidebar is persistent across all views

---

## Design Time Experience

### User Flow
1. Click `+ New Pipeline` → opens Design View with an objective input field
2. Type objective (e.g. *"analyze GitHub repos for security issues"*)
3. Click **Design Pipeline**
4. AI runs automatically: AgentMaster → AgentProducer → AgentCritique (≤5 iterations per agent)
5. UI streams live: each agent appears as a card as it is approved
6. AI infers the **input schema** — fields required at Run Time (name, type, required/optional, description)
7. When all agents complete: DAG visualization + agent card list displayed
8. User optionally renames the pipeline, then clicks **Save Pipeline**

### User Has No Required Interactions During Design
The entire design loop runs autonomously. The user watches, not decides.

### Error Case
If an agent cannot be approved after 5 critique iterations, it is displayed as a ⚠️ error card with the reason. The user can **Retry** (triggers redesign of that agent only) or **Discard Pipeline**.

---

## Run Time Experience

### User Flow
1. Click ▶ next to a pipeline in the sidebar → opens Run View
2. Pipeline name and description shown at top
3. Input form rendered from the pipeline's **input schema**:
   - Required fields: highlighted, block the Launch button if empty
   - Optional fields: shown with defaults (can be skipped)
   - Tokens/keys: masked input, never persisted beyond the session
4. Click **Launch** when ready
5. Live execution dashboard:
   - Agent status cards (PENDING → RUNNING → COMPLETE / ERROR)
   - Streaming execution log
   - DAG visualization with nodes lighting up on completion
6. Final output displayed when all agents finish

### Run History
- Each run is stored: `pipeline_id`, `inputs`, `status`, `started_at`, `completed_at`, `agent_results[]`
- A **Runs** tab per pipeline shows past executions with timestamp and status

---

## Backend API

### Pipeline Endpoints (Design Time)

| Method | Path | Description |
|---|---|---|
| `POST` | `/pipelines` | Create pipeline — accepts `objective`, returns `pipeline_id`, triggers design WebSocket |
| `GET` | `/ws/design/{pipeline_id}` | WebSocket — streams design events (blueprint, agent specs, critique results) |
| `GET` | `/pipelines` | List all saved pipelines |
| `GET` | `/pipelines/{id}` | Fetch pipeline detail (agents, DAG, input schema) |
| `PATCH` | `/pipelines/{id}` | Rename pipeline (name only — agents are not editable post-design) |
| `DELETE` | `/pipelines/{id}` | Delete pipeline |

### Run Endpoints (Run Time)

| Method | Path | Description |
|---|---|---|
| `POST` | `/runs` | Start a run — accepts `pipeline_id` + `inputs`, returns `run_id` |
| `GET` | `/ws/run/{run_id}` | WebSocket — streams execution events (agent state, outputs, errors) |
| `GET` | `/runs/{id}` | Fetch run result |
| `GET` | `/pipelines/{id}/runs` | List run history for a pipeline |

---

## Data Models

### Pipeline
```json
{
  "id": "pipeline_uuid",
  "name": "GitHub Security Analyzer",
  "objective": "analyze GitHub repos for security issues",
  "agents": [{ ...AtomicAgent }],
  "dag": { "nodes": [], "edges": [] },
  "input_schema": [
    { "name": "repo_url", "type": "url", "required": true, "description": "GitHub repository URL" },
    { "name": "github_token", "type": "secret", "required": true, "description": "GitHub Personal Access Token" },
    { "name": "branch", "type": "string", "required": false, "default": "main" }
  ],
  "quality_score": 8.5,
  "created_at": "2026-06-07T...",
  "updated_at": "2026-06-07T..."
}
```

### Run
```json
{
  "id": "run_uuid",
  "pipeline_id": "pipeline_uuid",
  "inputs": { "repo_url": "...", "github_token": "..." },
  "status": "PENDING | RUNNING | COMPLETED | FAILED",
  "started_at": "2026-06-07T...",
  "completed_at": "2026-06-07T...",
  "agent_results": [{ "agent_id": "...", "output": {}, "state": "COMPLETE" }]
}
```

---

## Frontend Component Map

| Component | Purpose |
|---|---|
| `Sidebar.tsx` | Pipeline list, + New Pipeline, ✏️/▶ per row |
| `DesignView.tsx` | Objective input form, design loop progress |
| `PipelineDesignStream.tsx` | Live agent cards during design (streams from `/ws/design/`) |
| `AgentCard.tsx` | Per-agent: name, state badge, critique panel |
| `DAGVisualization.tsx` | React Flow DAG with live node updates |
| `RunView.tsx` | Input form + Launch button + execution dashboard |
| `InputForm.tsx` | Dynamic form rendered from `input_schema` |
| `ExecutionDashboard.tsx` | Live agent status cards + execution log + DAG |
| `ExecutionLog.tsx` | Scrolling real-time trace log |
| `RunHistory.tsx` | Runs tab per pipeline |

---

## Deployment

### Backend — GCP Cloud Run
- Containerized via `Dockerfile` in `/backend`
- Stateless service; persistence via **Cloud SQL (PostgreSQL)** in production
- SQLite retained for local development
- Environment variables: `GEMINI_API_KEY`, `DATABASE_URL`, `CORS_ORIGINS`
- Service URL: `https://agentmaster-api-<hash>.run.app`

### Frontend — AWS S3 + CloudFront
- Vite static build deployed to S3 bucket + CloudFront distribution
- Single env var: `VITE_API_URL=https://agentmaster-api-<hash>.run.app`
- WebSocket connections: replace `https://` with `wss://` from the same base URL

### Local Development
- Backend: `uvicorn app.main:app --reload` on `localhost:8000`
- Frontend: `npm run dev` on `localhost:5173` with Vite proxy to backend
- SQLite database; `GEMINI_API_KEY` in `backend/.env`

### CI/CD — GitHub Actions
- **Backend pipeline**: on push to `main` → build Docker image → push to GCP Artifact Registry → deploy to Cloud Run
- **Frontend pipeline**: on push to `main` → `npm run build` → sync to S3 → invalidate CloudFront cache

---

## What Changes vs v1

| Area | v1 | v2 |
|---|---|---|
| Frontend pages | Home + Session | Shell + DesignView + RunView |
| Backend WebSocket | One `/ws/{session_id}` does everything | `/ws/design/{pipeline_id}` and `/ws/run/{run_id}` |
| Data model | `ExecutionSession` (merged) | `Pipeline` (design artifact) + `Run` (execution record) |
| Library | Passive auto-save after run | Explicit save gate after Design |
| Deployment | Local only | GCP (backend) + AWS (frontend) |

---

## Out of Scope (v2)
- Real-time collaboration / multi-user sessions
- Agent editing at Design Time (AI designs; user saves or discards)
- OAuth flows for permissions (paste token / API key only)
- Mobile-optimized layout
