# AgentMaster: Recursive Multi-Agent Orchestrator - Design Specification

**Date:** 2026-06-21  
**Status:** Design Approved  
**Architecture:** Clean Slate Rebuild - Hierarchical Multi-Agent Engine

---

## Executive Summary

AgentMaster is a recursive multi-agent orchestration system that decomposes user objectives into hierarchical agent graphs. The system spawns Sub-Agents that recursively break down complex tasks, Atomic Agents that execute single-purpose actions, and Critique Agents that enforce minimum 3-round validation with anti-hallucination guarantees.

**Key capabilities:**
- Domain-agnostic task execution (user defines domain: "Create PPT", "Book Tickets", "Software Development", etc.)
- Recursive task decomposition with 5-level depth limit
- Minimum 3-round critique validation on all outputs
- Dual UI: Studio (design/planning) + Control Room (live execution monitoring)
- Real-time WebSocket communication for all state changes
- Kill switch for graceful shutdown at any phase

---

## 1. System Architecture

### 1.1 Five-Layer Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator Layer                        │
│              (AgentMaster - Domain Classification)           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Sub-Agent Layer                           │
│         (Recursive Decomposition, Child Spawning)            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Atomic Agent Layer                         │
│        (Single-Action Executors with Tool Access)            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Critique Agent Layer                       │
│     (3+ Round Validation, Anti-Hallucination Enforcement)    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                       UI Layer                               │
│          Studio (Design) + Control Room (Execution)          │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Execution Flow

```
User Objective + Domain
         ↓
AgentMaster: Domain Classification & Initial Planning
         ↓
Root Sub-Agent Creation
         ↓
Recursive Decomposition (Sub-Agents spawn children)
         ↓
Atomic Agent Execution (with tool access)
         ↓
Critique Loop (minimum 3 rounds per output)
         ↓
Result Aggregation (up the hierarchy)
         ↓
Final Output to User
```

### 1.3 Technology Stack

- **Backend:** FastAPI (Python 3.11+)
- **Frontend:** React 18 + TypeScript + Vite
- **Database:** SQLite (with indexes for performance)
- **Real-time:** WebSocket (via FastAPI WebSocket support)
- **Graph Visualization:** React Flow or D3.js
- **Deployment:** GCP Cloud Run (europe-west1, us-central1)

---

## 2. Agent Types & Responsibilities

### 2.1 AgentMaster (Orchestrator)

**Role:** System entry point and domain classifier

**Input:**
- `objective`: Free-text user goal (e.g., "Create a 10-slide presentation on AI Safety")
- `domain`: User-specified domain (e.g., "Create PPT", "Book Tickets", "Software Development")
- `config`: Optional execution parameters (timeout, recursion depth, critique strictness)

**Responsibilities:**
1. Validate that objective is achievable
2. Use domain to inform decomposition strategy
3. Create root Sub-Agent with scoped task
4. Monitor overall execution graph
5. Handle escalations (human review needed, failures)

**Output:**
- Execution plan with root Sub-Agent assignment
- Domain classification reasoning (logged for audit)

**Anti-hallucination:**
- Cites domain classification logic
- Logs all decision rationale

### 2.2 Sub-Agent

**Role:** Task decomposer and child orchestrator

**Input:**
- Scoped task from parent (AgentMaster or another Sub-Agent)
- Domain context (inherited from parent)
- Recursion depth (current level in hierarchy)

**Responsibilities:**
1. Analyze task complexity (simple/medium/complex)
2. Decide decomposition strategy:
   - **Simple task:** Spawn Atomic Agents only
   - **Medium task:** Spawn Atomic Agents + 1-2 specialist Sub-Agents
   - **Complex task:** Spawn multiple child Sub-Agents
3. Create dependency graph (DAG) for children
4. Spawn children in topological order
5. Aggregate child outputs
6. Pass aggregated result to Critique Agents

**Complexity scoring:**
- Step count: 1-3 steps = simple, 4-10 = medium, 11+ = complex
- Domain breadth: Single sub-domain = simple, multi-domain = complex
- Uncertainty: Clear requirements = simple, ambiguous = complex

**Recursion rules:**
- Maximum depth: 5 levels (configurable)
- Maximum children per Sub-Agent: 10
- Breadth-first spawning (all children at one level before deeper recursion)

**Output:**
- Aggregated results from child agents
- Decomposition rationale (logged for audit)

**Anti-hallucination:**
- Each decomposition decision includes justification
- Citations for why task was split in a particular way

### 2.3 Atomic Agent

**Role:** Single-action executor with tool access

**Input:**
- Single, well-defined task (no AND conditions)
- Required input data from parent

**Responsibilities:**
1. Execute ONE action using available tools
2. Return structured output with citations/sources
3. Respect timeout limits
4. Be idempotent where possible

**Available tools:**
- `bash`: Execute shell commands
- `file_read`: Read file contents
- `file_write`: Write/create files
- `llm_call`: Make LLM API requests
- `web_search`: Search web for information
- `web_fetch`: Fetch URL content
- `git_operation`: Clone, commit, push, etc.
- `api_call`: HTTP requests to external APIs

**Output schema:**
```json
{
  "status": "completed" | "failed",
  "data": { /* structured result */ },
  "citations": [
    {"source_type": "file" | "url" | "command", "source": "path/url/cmd", "excerpt": "..."}
  ],
  "confidence": 0-100,
  "execution_time_ms": 1234
}
```

**Anti-hallucination:**
- MUST include citations for all claims
- Claims without citations auto-fail critique
- Tool outputs logged as provenance

### 2.4 Critique Agent

**Role:** Independent validator enforcing factual accuracy and completeness

**Input:**
- Output from any agent (Sub-Agent or Atomic Agent)
- Original task description (for context)

**Responsibilities:**
1. Run minimum 3 independent critique rounds
2. Verify factual claims against citations
3. Check task completeness
4. Validate consistency with parent requirements
5. Escalate to human if rounds disagree

**Three-round validation:**

**Round 1 - Factual Verification:**
- Check all claims against provided sources/citations
- Flag assertions without supporting evidence
- Verify tool outputs match agent claims
- **Verdict:** `facts_verified` (true/false) + unsupported claims list

**Round 2 - Completeness Check:**
- Did agent fully accomplish assigned task?
- Are there gaps or partial work?
- Do outputs match expected schema?
- **Verdict:** `task_complete` (true/false) + missing elements list

**Round 3 - Consistency Validation:**
- Cross-check output against parent task requirements
- Verify no contradictions with previous agent outputs
- Check logical coherence
- **Verdict:** `consistent` (true/false) + contradiction details

**Escalation logic:**
- Any round fails → agent retries (max 3 retries)
- Rounds disagree → automatic Round 4 with combined context
- Agent fails 3 retries → escalate to human review
- Rounds still disagree after Round 4 → human review

**Output schema:**
```json
{
  "verdict": "approved" | "rejected" | "needs_human_review",
  "round_results": [
    {
      "round": 1,
      "type": "factual_verification",
      "passed": true,
      "reasoning": "...",
      "unsupported_claims": []
    }
  ],
  "overall_confidence": 0-100
}
```

**Anti-hallucination enforcement:**
- Independent LLM context (not shared with critiqued agent)
- Different prompts/perspectives per round to avoid bias
- Low confidence (<70%) triggers additional round
- All critiques stored permanently for audit

---

## 3. Execution Graph & DAG Management

### 3.1 Graph Structure

**Nodes:** Individual agent instances (Sub-Agent or Atomic Agent)

**Node properties:**
- `agent_id`: UUID
- `agent_type`: sub_agent | atomic_agent
- `status`: pending | running | critique_phase | completed | failed | cancelled | human_review
- `parent_id`: UUID of spawning agent (null for root)
- `depth`: Recursion level (0 = root)
- `task_description`: What this agent does
- `input_data`: JSON
- `output_data`: JSON
- `citations`: JSON array
- `retry_count`: Integer
- `timeout_seconds`: Integer

**Edges:** Dependencies and data flow between agents

**Edge properties:**
- `from_agent_id`: UUID
- `to_agent_id`: UUID
- `data_description`: What flows along this edge

### 3.2 Execution Rules

1. **Topological execution:** Agents execute in dependency order (DAG traversal)
2. **Parallel execution:** Independent agents (no dependency edges) run concurrently
3. **Recursion trigger:** Sub-Agent spawns child Sub-Agents if complexity > threshold
4. **Depth limit:** Maximum 5 levels of Sub-Agent nesting (prevents infinite recursion)
5. **Critique gate:** No agent output propagates until critique validation passes
6. **Cycle detection:** System checks for circular dependencies before creating edges

### 3.3 Example Decomposition

**Objective:** "Create a 10-slide presentation on AI Safety"  
**Domain:** "Create PPT"

```
Root Sub-Agent (depth 0): "PresentationCreator"
├─ Child Sub-Agent (depth 1): "ContentResearcher"
│  ├─ Atomic Agent: "WebSearchAgent" (search AI Safety topics)
│  ├─ Atomic Agent: "DocumentReaderAgent" (read research papers)
│  └─ Atomic Agent: "OutlineSynthesizerAgent" (create content outline)
├─ Child Sub-Agent (depth 1): "SlideDesigner"
│  ├─ Atomic Agent: "TemplateSelector" (choose PPT template)
│  ├─ Atomic Agent: "SlideLayoutAgent" (design each slide layout)
│  └─ Atomic Agent: "VisualAssetFinder" (find images/diagrams)
└─ Atomic Agent: "PPTAssembler" (combine all into final .pptx file)
```

---

## 4. Data Model & Persistence

### 4.1 SQLite Database Schema

**`executions` table:**
```sql
CREATE TABLE executions (
    id TEXT PRIMARY KEY,  -- UUID
    objective TEXT NOT NULL,
    domain TEXT NOT NULL,
    status TEXT NOT NULL,  -- planning | running | completed | failed | stopped_by_user | human_review_needed
    root_agent_id TEXT,
    config JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    stopped_at TIMESTAMP,
    stopped_by TEXT,  -- user | timeout | error | system
    cancellation_reason TEXT
);
CREATE INDEX idx_executions_status ON executions(status);
CREATE INDEX idx_executions_created_at ON executions(created_at);
```

**`agents` table:**
```sql
CREATE TABLE agents (
    id TEXT PRIMARY KEY,  -- UUID
    execution_id TEXT NOT NULL,
    parent_id TEXT,  -- NULL for root
    agent_type TEXT NOT NULL,  -- sub_agent | atomic_agent
    depth INTEGER NOT NULL,
    task_description TEXT NOT NULL,
    status TEXT NOT NULL,  -- pending | running | critique_phase | completed | failed | cancelled | human_review
    input_data JSON,
    output_data JSON,
    citations JSON,
    retry_count INTEGER DEFAULT 0,
    timeout_seconds INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (execution_id) REFERENCES executions(id),
    FOREIGN KEY (parent_id) REFERENCES agents(id)
);
CREATE INDEX idx_agents_execution_id ON agents(execution_id);
CREATE INDEX idx_agents_parent_id ON agents(parent_id);
CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agents_type ON agents(agent_type);
```

**`edges` table:**
```sql
CREATE TABLE edges (
    id TEXT PRIMARY KEY,  -- UUID
    execution_id TEXT NOT NULL,
    from_agent_id TEXT NOT NULL,
    to_agent_id TEXT NOT NULL,
    data_description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (execution_id) REFERENCES executions(id),
    FOREIGN KEY (from_agent_id) REFERENCES agents(id),
    FOREIGN KEY (to_agent_id) REFERENCES agents(id)
);
CREATE INDEX idx_edges_execution_id ON edges(execution_id);
CREATE INDEX idx_edges_from ON edges(from_agent_id);
CREATE INDEX idx_edges_to ON edges(to_agent_id);
```

**`critiques` table:**
```sql
CREATE TABLE critiques (
    id TEXT PRIMARY KEY,  -- UUID
    agent_id TEXT NOT NULL,
    round_number INTEGER NOT NULL,
    critique_type TEXT NOT NULL,  -- factual_verification | completeness_check | consistency_validation
    verdict TEXT NOT NULL,  -- passed | failed
    reasoning TEXT NOT NULL,
    unsupported_claims JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);
CREATE INDEX idx_critiques_agent_id ON critiques(agent_id);
CREATE INDEX idx_critiques_round ON critiques(round_number);
```

**`tool_executions` table:**
```sql
CREATE TABLE tool_executions (
    id TEXT PRIMARY KEY,  -- UUID
    agent_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,  -- bash | file_read | file_write | llm_call | web_search | git_operation | api_call
    tool_input JSON NOT NULL,
    tool_output JSON,
    status TEXT NOT NULL,  -- running | completed | failed
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);
CREATE INDEX idx_tool_executions_agent_id ON tool_executions(agent_id);
CREATE INDEX idx_tool_executions_tool ON tool_executions(tool_name);
```

**`agent_templates` table (library):**
```sql
CREATE TABLE agent_templates (
    id TEXT PRIMARY KEY,  -- UUID
    name TEXT NOT NULL UNIQUE,
    domain_tags JSON,  -- Array of applicable domains
    template_spec JSON NOT NULL,  -- Reusable agent configuration
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_agent_templates_name ON agent_templates(name);
```

### 4.2 Performance Considerations

- **Indexes:** On execution_id, parent_id, status, agent_type for fast queries
- **Archival:** Move executions older than 30 days to archive table
- **WebSocket optimization:** Fetch only changed rows since last broadcast
- **Connection pooling:** Limit concurrent SQLite connections

---

## 5. Domain Classification & Binding

### 5.1 Domain as User Input

**User provides TWO inputs:**
1. **Objective:** Free-text description of goal
2. **Domain:** User-defined domain category (examples: "Create PPT", "Book Tickets", "Software Development", "Research", "Data Analysis", "Travel Planning", etc.)

**No domain restrictions:** System accepts ANY domain the user specifies.

### 5.2 Domain-Informed Decomposition

**How domain influences planning:**
- AgentMaster uses domain to select decomposition strategy
- Different domains → different agent patterns
  - "Create PPT" → content generation agents, formatting agents, visual design agents
  - "Book Tickets" → search agents, comparison agents, booking API agents
  - "Research" → web search agents, document readers, synthesis agents
  - "Software Development" → code analysis, testing, deployment agents

**Domain knowledge base:**
- System maintains heuristics/patterns per domain type
- Example patterns stored in agent_templates table with domain_tags
- Templates grow over time as system handles more domains

**Domain inheritance:**
- Sub-Agents inherit domain context from parent
- Domain influences tool selection (e.g., "Book Tickets" enables API call tools)

### 5.3 Domain-Specific Planning Examples

**Domain: "Create PPT"**
- Root Sub-Agent spawns: ContentResearcher → SlideDesigner → PPTAssembler
- Atomic Agents: WebSearchAgent, TemplateSelector, VisualAssetFinder

**Domain: "Book Tickets"**
- Root Sub-Agent spawns: RequirementsGatherer → SearchAgent → PriceComparator → BookingAgent
- Atomic Agents: FlightSearchAPI, HotelSearchAPI, PaymentProcessor

**Domain: "Software Development"**
- Root Sub-Agent spawns: CodeAnalyzer → TestRunner → Deployer
- Atomic Agents: GitCloner, LinterAgent, SecurityScanner, CITrigger

---

## 6. Dual UI System

### 6.1 Studio (Design/Planning Interface)

**Purpose:** Where users define objectives and approve execution plans BEFORE running.

**Route:** `/studio`

**Key features:**

**Objective Input Form:**
- Text area for objective description
- Domain input field (free text, user-defined)
- Optional parameters:
  - Max recursion depth (default: 5)
  - Timeout per agent (default: 300 seconds)
  - Critique strictness (standard | strict)
  - Parallel execution limit (default: 10 concurrent agents)

**DAG Visualization (Preview):**
- Shows planned agent hierarchy AFTER AgentMaster designs it
- Interactive force-directed graph (React Flow or D3.js)
- Node features:
  - Expandable Sub-Agents (click to see children)
  - Color-coded by type (Sub-Agent = blue, Atomic = green)
  - Hover shows: task description, estimated runtime, tool requirements
- Edge features:
  - Shows data flow direction
  - Labels describe payload

**Edit & Approve:**
- User can modify plan:
  - Remove agents
  - Adjust dependencies (drag edges)
  - Change agent parameters
- "Approve & Execute" button → transitions to Control Room
- "Save as Template" button → stores plan for reuse

**Template Library:**
- Browse previously executed plans by domain
- Filter by: domain, success rate, execution time
- Clone and modify existing plans
- Search by keywords

**Visual design:**
- Clean, modern interface
- Left panel: Input form + controls
- Center: DAG visualization (large canvas)
- Right panel: Agent details on selection

### 6.2 Control Room (Live Execution Monitor)

**Purpose:** Real-time monitoring of running agent graphs.

**Route:** `/control-room/:execution_id`

**Key features:**

**Live DAG Visualization:**
- Same graph structure as Studio, updates in real-time via WebSocket
- Color-coded agent status:
  - Gray: pending
  - Blue: running
  - Yellow: in critique phase
  - Green: completed
  - Red: failed
  - Orange: cancelled
  - Purple: human review needed
- Animations:
  - Pulsing borders on running agents
  - Rotating validation icons during critique
  - Particles flowing along edges (data transfer)
  - Progress bars on nodes (% completion for long-running agents)
- Hierarchical zoom: Click Sub-Agent → expands to show internal DAG
- Breadcrumb navigation to zoom back out
- Minimap in corner for overview when zoomed in

**Agent Detail Panel (right sidebar):**
- Click any node → see details:
  - Task description
  - Input/output data
  - Citations/sources
  - Tool executions (for Atomic Agents)
    - Bash commands run
    - Files read/written
    - API calls made
  - Critique rounds (for agents in/past critique phase)
    - Each round's verdict + reasoning
    - Unsupported claims flagged
  - Execution timeline
  - Retry history

**Event Stream (bottom panel):**
- Chronological feed of all events
- Event types:
  - Agent created/started/completed/failed
  - Critique round started/completed
  - Tool execution started/completed
  - Sub-Agent spawned
  - Human review requested
- Filters: by agent type, status, domain
- Search bar for keywords
- Auto-scroll to latest (toggle)

**Live Metrics Dashboard (top bar):**
- Total agents: X running, Y completed, Z failed
- Execution time elapsed (live clock)
- Tokens consumed (for LLM calls)
- Critique pass rate (X% approved first try)
- Estimated time remaining (based on current velocity)

**Intervention Controls:**
- **Stop Execution** button (red, prominent):
  - Graceful shutdown: wait up to 30s for agents to finish
  - Force kill option if timeout
  - Confirmation dialog: "Are you sure? X agents running"
- **Pause Execution** button:
  - Stops spawning new agents
  - Lets current ones finish
  - Resume button appears
- **Per-agent controls:**
  - Right-click any running agent → "Stop this agent" (recursive stop of descendants)
- **Retry failed agent:** Click failed node → "Retry" button

**Notifications:**
- Toast pop-ups for critical events:
  - Agent failures
  - Human review needed
  - Execution complete
  - Critique failures
- Sound effects (optional toggle):
  - Completion chime
  - Failure alert

**Visual design:**
- Dark theme optimized for monitoring
- Center: Large DAG canvas
- Right: Agent detail panel (collapsible)
- Bottom: Event stream (collapsible)
- Top: Metrics bar + controls

### 6.3 Real-Time Communication

**WebSocket events (pushed from backend):**

**Agent lifecycle:**
- `agent_created`: New agent added to graph
- `agent_started`: Agent begins execution
- `agent_running`: Progress update (for long-running agents)
- `agent_completed`: Agent finished successfully
- `agent_failed`: Agent encountered error

**Critique events:**
- `critique_round_started`: Round X begins
- `critique_round_completed`: Round X verdict
- `critique_passed`: All rounds approved
- `critique_failed`: Agent needs retry

**Tool execution (Atomic Agents):**
- `tool_started`: Tool invoked
- `tool_output`: Tool returned result
- `tool_failed`: Tool error

**Graph changes:**
- `subagent_spawned`: New Sub-Agent created
- `edge_created`: New dependency added
- `recursion_triggered`: Sub-Agent going deeper

**Execution-level:**
- `execution_started`: Run began
- `execution_paused`: User paused
- `execution_resumed`: User resumed
- `execution_stopped`: User stopped (or timeout/error)
- `execution_completed`: All agents finished
- `human_review_needed`: Escalation required

**Event payload format:**
```json
{
  "event_type": "agent_completed",
  "timestamp": "2026-06-21T10:30:45Z",
  "execution_id": "uuid",
  "agent_id": "uuid",
  "data": { /* event-specific data */ }
}
```

**No polling:** UI never polls for updates. Backend pushes all state changes instantly via WebSocket.

---

## 7. Execution Control & Kill Switch

### 7.1 Design Phase Controls (Studio)

**Cancel button:**
- Always visible during plan generation
- Aborts AgentMaster's planning immediately
- State transition: `planning` → `cancelled`
- Cleanup: Deletes incomplete execution record, releases resources
- UI feedback: "Plan generation cancelled" toast + return to input form

### 7.2 Run Phase Controls (Control Room)

**Stop Execution (graceful shutdown):**
1. User clicks "Stop Execution" button
2. Confirmation dialog: "Are you sure? X agents are currently running"
3. On confirm:
   - Mark execution: `running` → `stopping`
   - Send stop signal to all `running` agents
   - Wait up to 30 seconds for agents to finish current operation
   - Mark incomplete agents as `cancelled`
   - Final execution status: `stopped_by_user`
   - WebSocket broadcast: `execution_stopped` event
4. UI shows: "Execution stopped. X agents completed, Y cancelled."

**Force kill:**
- If graceful shutdown times out (>30s), "Force Stop" button appears
- On click:
  - Immediately terminates all agent processes
  - No waiting for cleanup
  - May leave partial outputs/dirty state
  - Logs warning about forced termination
- Confirmation dialog: "Warning: May leave incomplete state. Continue?"

**Pause/Resume:**
- **Pause button:**
  - Stops spawning new agents
  - Lets current agents finish their work
  - Status: `running` → `paused`
  - UI shows: "Paused. X agents running (will complete)."
- **Resume button:**
  - Continues from where it left off
  - Status: `paused` → `running`
  - Spawns next agents in queue

**Per-agent stop:**
- Right-click any running agent in DAG
- "Stop this agent" option
- Stops single agent + all its descendants (recursive stop)
- Parent agent receives `child_stopped` signal, can adapt plan

### 7.3 Database Tracking

**`executions` table additions:**
- `stopped_at`: Timestamp of stop request
- `stopped_by`: user | timeout | error | system
- `cancellation_reason`: Optional text from user

**`agents` table additions:**
- Status includes: `cancelled`
- Track which agents were running when stop occurred

### 7.4 Safety Confirmations

**Stop during run:**
- Dialog: "Are you sure? X agents are currently running. This will cancel incomplete work."
- Options: "Cancel" (go back) | "Stop Gracefully" | "Force Kill"

**Force kill:**
- Dialog: "Warning: Force kill may leave incomplete state, partial files, or dirty data. Continue?"
- Options: "Cancel" (go back) | "Force Kill"

---

## 8. Recursive Decomposition Algorithm

### 8.1 Complexity Scoring

Sub-Agents analyze assigned tasks using LLM to score on three dimensions:

**Step count:**
- 1-3 distinct actions = simple (score: 1)
- 4-10 actions = medium (score: 2)
- 11+ actions = complex (score: 3)

**Domain breadth:**
- Single sub-domain = simple (score: 1)
- 2-3 sub-domains = medium (score: 2)
- 4+ sub-domains or cross-domain = complex (score: 3)

**Uncertainty:**
- Clear, explicit requirements = simple (score: 1)
- Some ambiguity or missing details = medium (score: 2)
- Highly ambiguous or exploratory = complex (score: 3)

**Total complexity score:** Sum of three dimensions (3-9)
- 3-4 = Simple → spawn Atomic Agents only
- 5-6 = Medium → spawn Atomic Agents + 1-2 specialist Sub-Agents
- 7-9 = Complex → spawn multiple child Sub-Agents

### 8.2 Decomposition Process

**Step-by-step:**
1. Sub-Agent receives task from parent
2. LLM analyzes task and scores complexity
3. **If simple (3-4):**
   - Break into atomic steps (each becomes Atomic Agent)
   - Create edges showing dependencies
   - Spawn Atomic Agents
4. **If medium (5-6):**
   - Identify 1-2 complex sub-tasks
   - Create child Sub-Agents for complex parts
   - Create Atomic Agents for simple parts
   - Define dependencies between them
   - Spawn children
5. **If complex (7-9):**
   - Break into 2-N major sub-tasks
   - Each becomes child Sub-Agent
   - Create dependency graph
   - Spawn children breadth-first
6. Wait for all children to complete (and pass critique)
7. Aggregate results
8. Pass to critique

### 8.3 Recursion Safety Limits

**Max depth:** 5 levels (configurable in execution config)
- Prevents infinite recursion
- Enforced at spawn time: if `current_depth >= max_depth`, force Atomic Agent creation

**Max children per Sub-Agent:** 10
- Prevents exponential explosion
- If decomposition would create >10 children, Sub-Agent must re-group tasks

**Breadth-first spawning:**
- Sub-Agent spawns all children at same depth level
- Waits for children to start before any child recurses deeper
- Prevents runaway depth-first explosion

**Cycle detection:**
- Before creating edge, check if it would create cycle in DAG
- If cycle detected, reject edge and log error
- Parent Sub-Agent must re-plan

### 8.4 Decomposition Audit Trail

Every decomposition decision logged to database:
- Task received
- Complexity score breakdown
- Reasoning for decomposition choice
- Children spawned (IDs, tasks)
- Edges created

Stored in agents table `output_data` field as:
```json
{
  "decomposition": {
    "complexity_score": 7,
    "reasoning": "Task spans multiple domains (research + design + assembly) and has 12 distinct steps.",
    "children_spawned": [
      {"agent_id": "uuid", "task": "Research AI Safety topics"},
      {"agent_id": "uuid", "task": "Design slide layouts"}
    ],
    "edges_created": [
      {"from": "uuid1", "to": "uuid2", "payload": "content outline"}
    ]
  }
}
```

---

## 9. Backend Architecture

### 9.1 FastAPI Application Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Environment variables, settings
│   ├── database.py             # SQLite connection, models (SQLAlchemy)
│   ├── models/
│   │   ├── execution.py        # Execution ORM model
│   │   ├── agent.py            # Agent ORM model
│   │   ├── edge.py             # Edge ORM model
│   │   ├── critique.py         # Critique ORM model
│   │   ├── tool_execution.py   # ToolExecution ORM model
│   │   └── agent_template.py   # AgentTemplate ORM model
│   ├── schemas/
│   │   ├── execution.py        # Pydantic schemas for API
│   │   ├── agent.py
│   │   ├── critique.py
│   │   └── websocket.py        # WebSocket event schemas
│   ├── api/
│   │   ├── routes/
│   │   │   ├── executions.py   # POST /api/executions, GET /api/executions/:id
│   │   │   ├── agents.py       # GET /api/agents/:id
│   │   │   ├── templates.py    # GET /api/templates, POST /api/templates
│   │   │   └── health.py       # GET /health
│   │   └── websockets/
│   │       ├── studio.py       # WS /ws/studio/:execution_id (planning phase)
│   │       └── control_room.py # WS /ws/control-room/:execution_id (run phase)
│   ├── agents/
│   │   ├── orchestrator.py     # AgentMaster implementation
│   │   ├── sub_agent.py        # Sub-Agent implementation
│   │   ├── atomic_agent.py     # Atomic Agent base class
│   │   ├── critique_agent.py   # Critique Agent implementation
│   │   └── tools/
│   │       ├── bash.py         # Bash tool
│   │       ├── file_ops.py     # File read/write tools
│   │       ├── llm.py          # LLM API calls
│   │       ├── web.py          # Web search/fetch
│   │       ├── git.py          # Git operations
│   │       └── api_call.py     # Generic HTTP API tool
│   ├── services/
│   │   ├── execution_manager.py   # Orchestrates execution lifecycle
│   │   ├── graph_builder.py       # DAG construction and validation
│   │   ├── websocket_manager.py   # Broadcast events to connected clients
│   │   └── template_service.py    # Agent template CRUD
│   └── utils/
│       ├── logging.py          # Structured logging
│       └── metrics.py          # Token counting, timing
├── requirements.txt
└── Dockerfile
```

### 9.2 Key Components

**AgentMaster (orchestrator.py):**
- Receives user objective + domain
- Classifies and validates
- Creates root Sub-Agent
- Monitors execution graph
- Handles escalations

**Sub-Agent (sub_agent.py):**
- Scores task complexity
- Decomposes into children (Sub-Agents or Atomic Agents)
- Spawns children via execution_manager
- Aggregates results
- Passes to critique

**Atomic Agent (atomic_agent.py):**
- Base class with `execute()` method
- Tool access via tools/ modules
- Returns structured output with citations
- Timeout enforcement

**Critique Agent (critique_agent.py):**
- Runs 3+ independent LLM calls
- Each round has specific prompt (factual/completeness/consistency)
- Returns verdict per round
- Aggregates into final approval/rejection

**Execution Manager (execution_manager.py):**
- Orchestrates agent lifecycle
- Manages agent queue (topological order)
- Enforces concurrency limits
- Handles retries and failures
- Broadcasts WebSocket events

**Graph Builder (graph_builder.py):**
- Constructs DAG from agent spawning
- Validates no cycles
- Topological sort for execution order
- Edge creation and validation

**WebSocket Manager (websocket_manager.py):**
- Maintains connected client list per execution
- Broadcasts events to all clients
- Handles client connect/disconnect

### 9.3 Execution Flow (Backend)

1. **User creates execution via POST /api/executions**
   - Body: `{objective, domain, config}`
   - Returns: `{execution_id, status: "planning"}`
2. **User connects to WS /ws/studio/:execution_id**
3. **Backend spawns AgentMaster**
   - AgentMaster analyzes objective
   - Creates root Sub-Agent
   - Broadcasts `agent_created` events
4. **Root Sub-Agent decomposes**
   - Spawns children
   - Broadcasts `subagent_spawned`, `edge_created`
5. **User approves plan in Studio**
   - Sends `{action: "approve"}` message via WS
6. **Backend transitions to run phase**
   - Execution status: `planning` → `running`
   - Broadcasts `execution_started`
   - User switches to `/control-room/:execution_id` route
7. **User connects to WS /ws/control-room/:execution_id**
8. **Execution Manager runs agents**
   - Topological order
   - Parallel where possible
   - Broadcasts agent lifecycle events
9. **Each agent output → Critique Agent**
   - 3 rounds run
   - Broadcasts `critique_round_started`, `critique_round_completed`
   - If pass → agent status: `critique_phase` → `completed`
   - If fail → retry (max 3)
10. **All agents complete**
    - Execution status: `running` → `completed`
    - Broadcasts `execution_completed`

---

## 10. Frontend Architecture

### 10.1 React Application Structure

```
frontend/
├── src/
│   ├── main.tsx                # Entry point
│   ├── App.tsx                 # Root component, router
│   ├── pages/
│   │   ├── StudioPage.tsx      # /studio route
│   │   └── ControlRoomPage.tsx # /control-room/:id route
│   ├── components/
│   │   ├── studio/
│   │   │   ├── ObjectiveForm.tsx       # Input form
│   │   │   ├── PlanDAG.tsx             # DAG visualization (preview)
│   │   │   ├── AgentNodePreview.tsx    # Node component for plan view
│   │   │   ├── PlanEditor.tsx          # Edit/approve controls
│   │   │   └── TemplateLibrary.tsx     # Browse saved templates
│   │   ├── control-room/
│   │   │   ├── LiveDAG.tsx             # Real-time DAG visualization
│   │   │   ├── AgentNodeLive.tsx       # Node component with status
│   │   │   ├── AgentDetailPanel.tsx    # Right sidebar details
│   │   │   ├── EventStream.tsx         # Bottom event feed
│   │   │   ├── MetricsDashboard.tsx    # Top bar metrics
│   │   │   ├── ExecutionControls.tsx   # Stop/pause/resume buttons
│   │   │   └── Notifications.tsx       # Toast notifications
│   │   └── shared/
│   │       ├── DAGCanvas.tsx           # Shared graph rendering (React Flow)
│   │       └── StatusBadge.tsx         # Color-coded status indicator
│   ├── hooks/
│   │   ├── useWebSocket.ts     # WebSocket connection management
│   │   ├── useExecution.ts     # Fetch execution data
│   │   └── useAgentDetails.ts  # Fetch agent details
│   ├── services/
│   │   ├── api.ts              # HTTP API client (axios)
│   │   └── websocket.ts        # WebSocket client wrapper
│   ├── types/
│   │   ├── execution.ts        # TypeScript types
│   │   ├── agent.ts
│   │   ├── critique.ts
│   │   └── websocket.ts
│   └── utils/
│       ├── dagLayout.ts        # Graph layout algorithm
│       └── statusColors.ts     # Color mapping for statuses
├── package.json
├── tsconfig.json
├── vite.config.ts
└── Dockerfile
```

### 10.2 Key Components

**StudioPage:**
- Renders ObjectiveForm + PlanDAG + PlanEditor
- Manages WebSocket connection to `/ws/studio/:id`
- Handles plan approval → triggers transition to Control Room

**ControlRoomPage:**
- Renders LiveDAG + AgentDetailPanel + EventStream + MetricsDashboard + ExecutionControls
- Manages WebSocket connection to `/ws/control-room/:id`
- Real-time updates from backend events

**LiveDAG (React Flow-based):**
- Renders nodes (AgentNodeLive) and edges
- Color-coded by status
- Animations (pulsing, particles)
- Zoom/pan controls
- Minimap

**AgentDetailPanel:**
- Shows selected agent details
- Tabs: Overview | Input/Output | Tools | Critique | Timeline
- Real-time updates when agent state changes

**EventStream:**
- Reverse-chronological feed
- Filters by type/status
- Auto-scroll toggle
- Search bar

**ExecutionControls:**
- Stop/Pause/Resume buttons
- Confirmation dialogs
- Status indicators

### 10.3 WebSocket Integration

**useWebSocket hook:**
```typescript
const useWebSocket = (url: string) => {
  const [events, setEvents] = useState<WebSocketEvent[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');

  useEffect(() => {
    const ws = new WebSocket(url);
    
    ws.onopen = () => setConnectionStatus('connected');
    ws.onclose = () => setConnectionStatus('disconnected');
    ws.onmessage = (msg) => {
      const event = JSON.parse(msg.data);
      setEvents(prev => [...prev, event]);
    };

    return () => ws.close();
  }, [url]);

  return { events, connectionStatus };
};
```

**Event handling in ControlRoomPage:**
```typescript
const { events } = useWebSocket(`wss://api.agentmaster.com/ws/control-room/${executionId}`);

useEffect(() => {
  events.forEach(event => {
    switch (event.event_type) {
      case 'agent_created':
        // Add node to graph
        break;
      case 'agent_started':
        // Update node status to running
        break;
      case 'agent_completed':
        // Update node status to completed
        break;
      // ... handle all event types
    }
  });
}, [events]);
```

---

## 11. Deployment Architecture

### 11.1 GCP Cloud Run Deployment

**Two regional deployments:**
- **europe-west1** (primary)
- **us-central1** (secondary)

**Backend service:**
- Container: FastAPI app
- Auto-scaling: 1-10 instances
- CPU: 2 vCPU
- Memory: 4 GB
- Timeout: 3600 seconds (1 hour for long executions)
- Concurrency: 80 requests per instance

**Frontend service:**
- Container: Nginx serving static React build
- Auto-scaling: 1-5 instances
- CPU: 1 vCPU
- Memory: 512 MB

### 11.2 Database

**SQLite file storage:**
- Mounted on Cloud Run persistent volume (beta feature) OR
- GCS bucket with local caching (read from GCS on startup, write back periodically)

**Backup strategy:**
- Hourly snapshots to GCS
- 7-day retention

### 11.3 Environment Variables

**Backend:**
- `DATABASE_URL`: Path to SQLite file
- `GEMINI_API_KEY`: For LLM calls (Google Gemini)
- `OPENAI_API_KEY`: Fallback LLM
- `LOG_LEVEL`: info | debug
- `MAX_RECURSION_DEPTH`: Default 5
- `MAX_AGENT_TIMEOUT`: Default 300 seconds
- `WEBSOCKET_PING_INTERVAL`: Default 30 seconds

**Frontend:**
- `VITE_API_BASE_URL`: Backend API URL
- `VITE_WS_BASE_URL`: Backend WebSocket URL

### 11.4 CI/CD Pipeline

**GitHub Actions workflow:**
1. Run tests (pytest for backend, vitest for frontend)
2. Build Docker images
3. Push to Google Container Registry
4. Deploy to Cloud Run (europe-west1)
5. Smoke test
6. Deploy to Cloud Run (us-central1)

**Deployment script (deploy.sh):**
- Builds backend and frontend containers
- Pushes to GCR
- Updates Cloud Run services
- Runs health check

---

## 12. Implementation Phases

### Phase 1: Core Infrastructure (Week 1-2)
- SQLite database schema + migrations
- FastAPI app skeleton
- WebSocket manager
- Basic execution model (create, store, retrieve)
- Health check endpoints

### Phase 2: Agent Foundation (Week 3-4)
- AgentMaster (orchestrator) implementation
- Sub-Agent with basic decomposition
- Atomic Agent base class + 2-3 core tools (bash, file_read, llm_call)
- Graph Builder (DAG construction, validation)

### Phase 3: Critique System (Week 5)
- Critique Agent implementation
- 3-round validation logic
- Retry/escalation handling
- Anti-hallucination enforcement (citation checking)

### Phase 4: Execution Engine (Week 6-7)
- Execution Manager (topological execution, concurrency)
- WebSocket event broadcasting
- Kill switch (graceful/force stop, pause/resume)
- Template library (save/load)

### Phase 5: Frontend - Studio (Week 8-9)
- React app skeleton + routing
- ObjectiveForm component
- PlanDAG visualization (React Flow)
- Plan approval flow
- Template library UI

### Phase 6: Frontend - Control Room (Week 10-11)
- LiveDAG component
- Real-time WebSocket integration
- AgentDetailPanel
- EventStream
- MetricsDashboard
- ExecutionControls (stop/pause/resume)

### Phase 7: Tools & Domain Templates (Week 12)
- Additional Atomic Agent tools (web_search, git_operation, api_call)
- Domain-specific templates ("Create PPT", "Book Tickets", "Software Development")
- Template discovery/reuse logic

### Phase 8: Testing & Polish (Week 13-14)
- End-to-end tests (full execution flows)
- Performance optimization (database indexes, WebSocket efficiency)
- Error handling improvements
- UI/UX polish (animations, notifications, accessibility)

### Phase 9: Deployment & Documentation (Week 15-16)
- Cloud Run deployment setup
- CI/CD pipeline (GitHub Actions)
- User documentation
- API documentation (OpenAPI/Swagger)
- Monitoring/alerting setup

---

## 13. Success Criteria

### Functional Requirements
- ✅ System accepts any user-defined domain
- ✅ Recursive decomposition up to 5 levels
- ✅ Minimum 3-round critique validation on all outputs
- ✅ Kill switch works in both design and run phases
- ✅ Dual UI (Studio + Control Room) fully functional
- ✅ Real-time WebSocket updates with zero polling
- ✅ Template library saves and reuses successful plans
- ✅ Anti-hallucination: All outputs include citations

### Performance Requirements
- Sub-Agent decomposition completes in <10 seconds
- Atomic Agent execution respects timeout limits
- WebSocket latency <200ms for event delivery
- Support 100+ concurrent agents per execution
- Database queries <100ms (with indexes)
- Frontend rendering 60 FPS for DAG animations

### Reliability Requirements
- Graceful degradation on LLM API failures (retry logic)
- No data loss on system crash (SQLite transactions)
- WebSocket reconnection on connection drop
- Execution state recoverable from database

### Usability Requirements
- User can understand agent status at a glance (color coding)
- Critique failures show clear reasoning
- Agent detail panel shows all relevant info (no hidden state)
- Stop/pause actions confirm before destructive operations

---

## 14. Open Questions & Future Enhancements

### Current Scope Out-of-Bounds (for v1)
- Multi-user support (authentication, permissions)
- Execution history comparison ("diff" two runs)
- Agent marketplace (community templates)
- Cost optimization (LLM call caching, prompt compression)
- Distributed execution (agents run on separate workers)
- Agent code generation (auto-write Atomic Agent code from description)

### Potential Future Work
- **Execution replay:** Re-run execution with same inputs, compare outputs
- **Agent debugging:** Step-through mode, breakpoints on agents
- **Custom critique rules:** User-defined validation logic
- **Multi-modal agents:** Image/video processing tools
- **Agent learning:** Track which templates work best per domain
- **Collaborative planning:** Multiple users edit plan together
- **Export:** Download execution results as report (PDF, HTML)

---

## 15. Appendix

### 15.1 Agent Naming Conventions

**Sub-Agents:** PascalCase, descriptive noun (e.g., `PresentationCreator`, `ContentResearcher`)

**Atomic Agents:** PascalCase + "Agent" suffix (e.g., `WebSearchAgent`, `FileReaderAgent`)

**Critique Agents:** `CritiqueAgent_<round>` (e.g., `CritiqueAgent_Factual`)

### 15.2 Status Enums

**Execution statuses:**
- `planning`: AgentMaster designing plan
- `running`: Agents executing
- `paused`: User paused
- `stopping`: Graceful shutdown in progress
- `stopped_by_user`: User stopped execution
- `completed`: All agents finished successfully
- `failed`: Execution failed (unrecoverable error)
- `human_review_needed`: Critique escalation

**Agent statuses:**
- `pending`: Not yet started
- `running`: Executing
- `critique_phase`: Output being validated
- `completed`: Finished successfully
- `failed`: Encountered error
- `cancelled`: Stopped by user/parent
- `human_review`: Escalated for manual review

### 15.3 Color Palette (Status Colors)

- Pending: `#9CA3AF` (gray-400)
- Running: `#3B82F6` (blue-500)
- Critique Phase: `#F59E0B` (amber-500)
- Completed: `#10B981` (green-500)
- Failed: `#EF4444` (red-500)
- Cancelled: `#F97316` (orange-500)
- Human Review: `#A855F7` (purple-500)

### 15.4 Sample API Endpoints

**POST /api/executions**
```json
Request:
{
  "objective": "Create a 10-slide presentation on AI Safety",
  "domain": "Create PPT",
  "config": {
    "max_recursion_depth": 5,
    "agent_timeout_seconds": 300,
    "critique_strictness": "standard"
  }
}

Response:
{
  "id": "exec_123",
  "status": "planning",
  "created_at": "2026-06-21T10:00:00Z"
}
```

**GET /api/executions/:id**
```json
Response:
{
  "id": "exec_123",
  "objective": "Create a 10-slide presentation on AI Safety",
  "domain": "Create PPT",
  "status": "completed",
  "root_agent_id": "agent_root_456",
  "created_at": "2026-06-21T10:00:00Z",
  "completed_at": "2026-06-21T10:15:30Z"
}
```

**WS /ws/control-room/:id**
```json
Event (agent_completed):
{
  "event_type": "agent_completed",
  "timestamp": "2026-06-21T10:05:12Z",
  "execution_id": "exec_123",
  "agent_id": "agent_789",
  "data": {
    "agent_name": "WebSearchAgent",
    "output": { /* structured data */ },
    "citations": [
      {"source_type": "url", "source": "https://example.com/ai-safety", "excerpt": "..."}
    ]
  }
}
```

---

**End of Design Specification**
