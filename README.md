# AgentMaster

> **Autonomous Agentic Graph Framework (AAGF)** — AI-powered multi-agent DAG orchestration system

[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6)](https://typescriptlang.org)

---

## Overview

AgentMaster implements the AAGF specification — a framework where users describe **any objective** in natural language and the system:

1. **[DESIGN]** Decomposes the objective into atomic agents organized as a Directed Acyclic Graph (DAG)
2. **[DRYRUN]** Validates every agent in sandbox simulation with zero-error critique loops
3. **[RUN]** Executes agents against real systems with full observability

Three core agent classes collaborate:
- **AgentMaster** — Orchestrator that interprets objectives and designs blueprints
- **AgentProducer** — Builder that creates atomic agent specifications
- **AgentCritique** — Reviewer that enforces zero-error policy (up to 5 iterations per agent)

---

## Architecture

```
User Objective
      │
      ▼
┌─────────────┐     WebSocket      ┌──────────────────┐
│  React UI   │◄──────────────────►│  FastAPI Backend  │
│             │     REST API       │                   │
│ DAG Viewer  │◄──────────────────►│ AgentMaster LLM   │
│ Phase Panel │                    │ AgentProducer LLM  │
│ Agent Cards │                    │ AgentCritique LLM  │
│ Exec Log    │                    │                   │
└─────────────┘                    │ DAG Engine        │
                                   │ Agent Library     │
                                   │ SQLite DB         │
                                   └──────────────────┘
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- OpenAI API key

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
# Opens http://localhost:5173
```

---

## Environment Variables

```env
# backend/.env
OPENAI_API_KEY=sk-your-key-here       # Required for LLM agents
DATABASE_URL=sqlite:///./agentmaster.db
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=["http://localhost:5173"]
```

---

## Usage

1. Open `http://localhost:5173`
2. Enter any objective (e.g., *"Analyze my GitHub repo for security vulnerabilities"*)
3. Click **→ Launch AgentMaster**
4. Watch the system:
   - Search the Agent Library for reusable patterns
   - Design an atomic agent DAG blueprint
   - Run each agent through up to 5 critique iterations
   - Display the live DAG visualization
   - Stream all events to the execution log

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/sessions` | Create execution session |
| `GET` | `/api/sessions/{id}` | Get session state |
| `POST` | `/api/sessions/{id}/input` | Provide missing input |
| `GET` | `/api/library` | List Agent Library |
| `GET` | `/api/library/search?q=...` | Search library |
| `WS` | `/ws/{session_id}` | Real-time event stream |

---

## Testing

```bash
cd backend
.venv\Scripts\activate
pytest tests/ -v
```

Current test coverage:
- ✅ Data models (AtomicAgent, DAGGraph, ExecutionSession)
- ✅ DAG engine (ready nodes, injection, completion)
- ✅ Lifecycle state machine (transitions, invalid transitions, critique counting)
- ✅ Agent Library (save, search, retrieve)
- ✅ FastAPI routes (health, sessions CRUD, library, input)
- ✅ Critique loop (5-iteration zero-error policy, approval, escalation)

---

## Project Structure

```
AgentMaster/
├── backend/
│   ├── app/
│   │   ├── agents/          # AgentMaster, AgentProducer, AgentCritique
│   │   ├── api/             # FastAPI routes + WebSocket
│   │   ├── engine/          # DAG engine + lifecycle state machine
│   │   ├── library/         # Agent Library persistence
│   │   ├── models/          # Pydantic + SQLAlchemy models
│   │   ├── prompts/         # LLM system prompts (AAGF spec)
│   │   └── main.py          # FastAPI app entry point
│   ├── tests/               # pytest test suite
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/             # Axios HTTP client
│   │   ├── components/      # DAGVisualization, AgentCard, etc.
│   │   ├── hooks/           # useWebSocket, useSession
│   │   ├── pages/           # Home, Session
│   │   ├── store/           # Zustand session store
│   │   └── types/           # Shared TypeScript types
│   └── package.json
└── docs/
    └── superpowers/
        ├── specs/           # Design specification
        └── plans/           # Implementation plan
```

---

## Key Design Principles (from AAGF Spec)

### 6 Laws of Atomic Agents
1. **Single Action** — One agent, one action. No "and".
2. **Defined Contract** — Full `input_schema`, `output_schema`, `error_schema`
3. **Idempotent** — Same input → same output always
4. **Observable** — Emits STARTED/PROGRESS/WAITING/COMPLETED/FAILED events
5. **Self-Describing** — Agent can explain itself
6. **Isolated** — No access outside declared input contract

### Zero-Error Policy
Critique loops run up to 5 iterations. Errors are **never** passed forward — they trigger auto-fix, rethink, or user escalation.

---

## License

MIT
