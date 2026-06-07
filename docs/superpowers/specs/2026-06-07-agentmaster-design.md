# AgentMaster — Design Spec
**Date:** 2026-06-07  
**Version:** 1.0  
**Source:** AAGF_System_Prompt_v3.docx

---

## Overview

AgentMaster is a full-stack implementation of the Autonomous Agentic Graph Framework (AAGF). It enables users to describe ANY objective in natural language; the system decomposes it into atomic, DAG-ordered agents, critiques each agent through up to 5 iterations, and executes the validated graph against real systems — with full observability at every step.

---

## Architecture

### Three-Tier Stack
- **Backend**: Python 3.11+, FastAPI, WebSockets, SQLAlchemy, Pydantic
- **Frontend**: React 18 + TypeScript, Vite, TailwindCSS, React Flow (DAG viz)
- **LLM Layer**: OpenAI GPT-4o (configurable via env), LangChain for prompt management
- **Persistence**: SQLite via SQLAlchemy (Agent Library + session state)

### Core Agent Classes

| Class | Role |
|---|---|
| `AgentMaster` | Orchestrator — interprets objective, searches library, builds blueprint, manages phases |
| `AgentProducer` | Builder — instantiates atomic agents per DAG specification |
| `AgentCritique` | Reviewer — reviews every agent output up to 5 iterations, zero-error policy |

### Tri-Phase Operation

```
[DESIGN] → [DRYRUN] → [RUN]
```

- **DESIGN TIME**: LLM builds agent DAG specifications, critique reviews each spec (≤5 iterations)
- **DRY RUN**: Every agent executes in sandboxed simulation; errors trigger critique-fix loop
- **RUN TIME**: Agents execute against real systems; results accumulate into final deliverable

---

## Component Design

### Backend (`/backend`)

```
backend/
├── app/
│   ├── agents/
│   │   ├── agent_master.py      # Orchestrator LLM agent
│   │   ├── agent_producer.py    # Atomic agent builder
│   │   └── agent_critique.py   # Reviewer with 5-iter loop
│   ├── engine/
│   │   ├── dag.py               # DAG data structure + mutation
│   │   ├── executor.py          # Phase execution engine
│   │   └── lifecycle.py         # Agent state machine
│   ├── library/
│   │   └── agent_library.py     # SQLite-backed catalog of reusable flows
│   ├── api/
│   │   ├── routes/
│   │   │   ├── sessions.py      # CRUD for execution sessions
│   │   │   ├── agents.py        # Agent management endpoints
│   │   │   └── library.py       # Agent Library CRUD
│   │   └── websocket.py         # Real-time streaming endpoint
│   ├── models/
│   │   ├── agent.py             # Pydantic + ORM models for agents
│   │   ├── dag.py               # DAG node/edge models
│   │   └── session.py           # Session and state models
│   ├── prompts/
│   │   ├── master.py            # AgentMaster system prompt
│   │   ├── producer.py          # AgentProducer system prompt
│   │   └── critique.py          # AgentCritique system prompt
│   └── main.py                  # FastAPI app entry point
├── tests/
└── requirements.txt
```

### Frontend (`/frontend`)

```
frontend/
├── src/
│   ├── components/
│   │   ├── DAGVisualization/    # React Flow DAG graph
│   │   ├── PhaseIndicator/      # DESIGN/DRYRUN/RUN banner
│   │   ├── AgentCard/           # Per-agent status + critique panel
│   │   ├── InputCollector/      # Dynamic input prompt UI
│   │   ├── LibraryBrowser/      # Agent Library catalog
│   │   └── ExecutionLog/        # Real-time trace log
│   ├── hooks/
│   │   ├── useWebSocket.ts      # WebSocket event streaming
│   │   └── useSession.ts        # Session state management
│   ├── pages/
│   │   ├── Home.tsx             # Objective input landing
│   │   └── Session.tsx          # Live execution dashboard
│   └── App.tsx
├── package.json
└── vite.config.ts
```

---

## Data Flow

1. User enters objective → POST `/api/sessions` → AgentMaster initializes
2. AgentMaster streams events over WebSocket → frontend renders DAG nodes live
3. Each AgentProducer creates an agent spec → AgentCritique reviews (loop ≤5)
4. Approved DAG → DryRun phase → sandbox simulation
5. All agents pass → RunTime phase → real execution
6. Final results pushed over WebSocket → session stored in Agent Library

---

## Key Data Models

### AtomicAgent
```json
{
  "agent_id": "agent_001",
  "agent_name": "GitHubRepoAnalyzer",
  "phase": "design_time | dry_run | run_time",
  "state": "PENDING → SPECIFYING → APPROVED",
  "input_schema": {},
  "output_schema": {},
  "error_schema": {},
  "required_user_inputs": [],
  "timeout_seconds": 60,
  "retry_policy": {"max_retries": 3, "backoff": "exponential"},
  "critique_iterations": 0,
  "quality_score": null
}
```

### CritiqueResult
```json
{
  "critique_id": "agent_001_critique_iter_1",
  "target_agent": "agent_001",
  "iteration": 1,
  "max_iterations": 5,
  "verdict": "APPROVED | NEEDS_REVISION | ESCALATE_*",
  "quality_score": 8,
  "issues": [],
  "remaining_errors": []
}
```

### DAGEdge
```json
{
  "edge_id": "e_001_002",
  "from_agent": "agent_001",
  "to_agent": "agent_002",
  "payload_schema": {}
}
```

---

## Error Handling

- Critique loop: max 5 iterations → auto-fix attempt → rethink → user escalation
- All errors are logged with `agent_id`, `iteration`, `error_type`
- Errors NEVER propagate to downstream agents
- Failed sessions are recoverable from last validated checkpoint

---

## Agent Library

- SQLite table: `agent_patterns` (id, name, domain, objective, dag_json, quality_score, created_at)
- Searched on every new session via semantic similarity (cosine on embeddings)
- New approved flows auto-saved after RunTime completion

---

## Testing Strategy

- Unit tests for DAG engine, lifecycle state machine, critique loop logic
- Integration tests for agent orchestration flow (mocked LLM)
- E2E test: submit sample objective, verify full DESIGN→DRYRUN→RUN cycle

---

## Implementation Plan Summary

1. Bootstrap project (git, GitHub repo, Python venv, Node packages)
2. Build data models (Pydantic + SQLAlchemy)
3. Build DAG engine + lifecycle state machine
4. Implement LLM agents (Master, Producer, Critique) with prompts from spec
5. Build FastAPI routes + WebSocket streaming
6. Build React frontend (DAG viz, phase indicator, agent cards)
7. Wire frontend ↔ backend
8. Agent Library persistence
9. Tests + README
10. Final commit + GitHub push
