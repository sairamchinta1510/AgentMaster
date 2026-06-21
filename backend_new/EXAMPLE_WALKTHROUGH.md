# Example Use Case: AgentMaster Backend Demonstration

## Overview

This example demonstrates AgentMaster's recursive multi-agent orchestration with a real-world scenario:

**Use Case:** Create a comprehensive 5-page training document on Python Best Practices for junior developers.

**Domain:** Content Generation

**What It Demonstrates:**
- ✅ Domain-agnostic task execution (user-defined domain)
- ✅ Recursive task decomposition (Sub-Agents spawning child agents)
- ✅ Tool execution (web search, LLM calls, file operations)
- ✅ Critique validation (3-round validation with anti-hallucination)
- ✅ Real-time monitoring via WebSockets
- ✅ Complete execution lifecycle

---

## Running the Example

### Terminal 1: Start Backend

```bash
cd backend_new

# Create virtual environment (first time only)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn app.main:app --reload
```

Wait for: `Application startup complete.`

### Terminal 2: Run Example

```bash
cd backend_new

# Activate virtual environment
source venv/bin/activate

# Run example
python example_use_case.py
```

---

## Expected Output

```
======================================================================
       Example Use Case: Create Technical Training Document       
======================================================================

Time: 2026-06-21 15:30:00
Objective: Create a 5-page training document on Python Best Practices
Domain: Content Generation

[Step 1] Creating Execution via REST API
→ Sending POST request to http://localhost:8000/api/executions
→ Objective: Create a comprehensive 5-page training document on Python Best...
✓ Execution created: exec_abc123
→ Status: planning
→ Root Agent: agent_root_001

[Step 2] Connecting to Studio WebSocket (Planning Phase)
→ WebSocket URL: ws://localhost:8000/ws/studio/exec_abc123
✓ Connected to Studio WebSocket
→ Monitoring agent planning...
✓ Agent planned: [sub_agent] PresentationCreator
✓ Agent planned: [sub_agent] ContentResearcher
✓ Agent planned: [atomic_agent] WebSearchAgent
✓ Agent planned: [atomic_agent] DocumentReaderAgent
✓ Agent planned: [atomic_agent] OutlineSynthesizerAgent
✓ Agent planned: [sub_agent] DocumentFormatter
✓ Agent planned: [atomic_agent] SectionWriterAgent
✓ Agent planned: [atomic_agent] ExampleGeneratorAgent
✓ Agent planned: [atomic_agent] DocumentAssembler
→ Dependency edge created
→ Dependency edge created
✓ Planning phase complete!

Planned Agents:
  1. [sub_agent] PresentationCreator
  2. [sub_agent] ContentResearcher
  3. [atomic_agent] WebSearchAgent
  4. [atomic_agent] DocumentReaderAgent
  5. [atomic_agent] OutlineSynthesizerAgent
  6. [sub_agent] DocumentFormatter
  7. [atomic_agent] SectionWriterAgent
  8. [atomic_agent] ExampleGeneratorAgent
  9. [atomic_agent] DocumentAssembler

[Step 3] Executing Agents via Control Room WebSocket
→ WebSocket URL: ws://localhost:8000/ws/control-room/exec_abc123
✓ Connected to Control Room WebSocket
→ Monitoring execution... (max 60 seconds)

✓ Execution started!

▶ Starting: [sub_agent] ContentResearcher
  → Critique Round 1 started
  → Round 1: passed
  → Critique Round 2 started
  → Round 2: passed
  → Critique Round 3 started
  → Round 3: passed
  ✓ Critique: approved (confidence: 95%)
✓ Completed: ContentResearcher

  → Sub-Agent spawned (recursive decomposition)

▶ Starting: [atomic_agent] WebSearchAgent
  → Critique Round 1 started
  → Round 1: passed
  → Critique Round 2 started
  → Round 2: passed
  → Critique Round 3 started
  → Round 3: passed
  ✓ Critique: approved (confidence: 95%)
✓ Completed: WebSearchAgent

▶ Starting: [atomic_agent] OutlineSynthesizerAgent
  → Critique Round 1 started
  → Round 1: passed
  → Critique Round 2 started
  → Round 2: passed
  → Critique Round 3 started
  → Round 3: passed
  ✓ Critique: approved (confidence: 95%)
✓ Completed: OutlineSynthesizerAgent

▶ Starting: [sub_agent] DocumentFormatter
  → Critique Round 1 started
  → Round 1: passed
  → Critique Round 2 started
  → Round 2: passed
  → Critique Round 3 started
  → Round 3: passed
  ✓ Critique: approved (confidence: 95%)
✓ Completed: DocumentFormatter

▶ Starting: [atomic_agent] SectionWriterAgent
  → Critique Round 1 started
  → Round 1: passed
  → Critique Round 2 started
  → Round 2: passed
  → Critique Round 3 started
  → Round 3: passed
  ✓ Critique: approved (confidence: 95%)
✓ Completed: SectionWriterAgent

▶ Starting: [atomic_agent] DocumentAssembler
  → Critique Round 1 started
  → Round 1: passed
  → Critique Round 2 started
  → Round 2: passed
  → Critique Round 3 started
  → Round 3: passed
  ✓ Critique: approved (confidence: 95%)
✓ Completed: DocumentAssembler

✓ EXECUTION COMPLETED!

[Step 4] Retrieving Final Execution Results
✓ Execution details retrieved
→ Final Status: completed
→ Created: 2026-06-21T15:30:00Z
→ Completed: 2026-06-21T15:31:45Z
→ Duration: 105.23 seconds

======================================================================
                        Execution Summary                        
======================================================================

Execution ID: exec_abc123
Agents Planned: 9
Agents Started: 6
Agents Completed: 6
Agents Failed: 0
Critique Verdicts: 6
  - Approved: 6
  - Rejected/Review: 0

What Happened:
1. AgentMaster created a root Sub-Agent for 'Content Generation' domain
2. Sub-Agent analyzed the objective and decomposed it into:
   - Research agents (gather Python best practices)
   - Content agents (write sections, create examples)
   - Formatting agents (structure the document)
3. Each Atomic Agent executed its task using tools:
   - web_search_tool (research best practices)
   - llm_call_tool (generate content)
   - file_write_tool (save document)
4. Critique Agents validated each output (3 rounds minimum)
5. Final document assembled and returned

✓ Use case demonstration complete!

Check the database for full details:
  sqlite3 agentmaster.db "SELECT * FROM agents WHERE execution_id='exec_abc123';"
```

---

## What's Happening Behind the Scenes

### 1. **Orchestrator (AgentMaster)**
- Receives: User objective + domain
- Validates: Objective is achievable
- Creates: Root Sub-Agent with depth=0
- Domain: Any user-defined domain (no restrictions)

### 2. **Recursive Decomposition (Sub-Agent)**
- Analyzes: Task complexity (3-9 scale)
  - Step count: 1-3 = simple, 4-10 = medium, 11+ = complex
  - Domain breadth: single vs multi-domain
  - Uncertainty: clear vs ambiguous
- Decomposes: Based on complexity score
  - Simple (3-4): Spawn Atomic Agents only
  - Medium (5-6): Mix of Atomic + 1-2 Sub-Agents
  - Complex (7-9): Multiple Sub-Agents (recursive)
- Enforces: Max depth 5, max 10 children per agent

### 3. **Tool Execution (Atomic Agents)**
- Selects tool based on input:
  - `"command"` → bash_tool
  - `"file_path" + "content"` → file_write_tool
  - `"file_path"` → file_read_tool
  - `"prompt"` → llm_call_tool (Gemini API)
- Logs: All tool executions to ToolExecution table
- Returns: Structured output with citations

### 4. **Validation (Critique Agent)**
- **Round 1:** Factual verification (checks citations exist)
- **Round 2:** Completeness check (task fully accomplished?)
- **Round 3:** Consistency validation (confidence >= 70%)
- **Round 4:** Combined review if 2/3 rounds pass
- **Auto-reject:** Outputs without citations
- **Retry:** Up to 3 retries on failure
- **Escalate:** Human review if retries exhausted

### 5. **Real-time Updates (WebSocket)**
- **Studio WS:** Planning phase events (agent_created, edge_created)
- **Control Room WS:** Execution events (agent_started, completed, failed)
- **Ping/keepalive:** 30-second intervals
- **Broadcast:** All state changes pushed to connected clients

---

## Architecture Visualization

```
User Request
     ↓
AgentMaster (Orchestrator)
     ↓
Root Sub-Agent (depth=0)
     ├─→ Sub-Agent: ContentResearcher (depth=1)
     │    ├─→ Atomic: WebSearchAgent (depth=2)
     │    │    └─→ Tool: web_search_tool
     │    │    └─→ Critique: 3 rounds → approved
     │    ├─→ Atomic: DocumentReaderAgent (depth=2)
     │    └─→ Atomic: OutlineSynthesizerAgent (depth=2)
     │         └─→ Tool: llm_call_tool (Gemini)
     │         └─→ Critique: 3 rounds → approved
     │
     ├─→ Sub-Agent: DocumentFormatter (depth=1)
     │    ├─→ Atomic: SectionWriterAgent (depth=2)
     │    │    └─→ Tool: llm_call_tool
     │    │    └─→ Critique: 3 rounds → approved
     │    └─→ Atomic: ExampleGeneratorAgent (depth=2)
     │
     └─→ Atomic: DocumentAssembler (depth=1)
          └─→ Tool: file_write_tool
          └─→ Critique: 3 rounds → approved
```

---

## Database Inspection

After running the example, inspect the database:

```bash
cd backend_new
sqlite3 agentmaster.db
```

### View Execution
```sql
SELECT * FROM executions WHERE id='exec_abc123';
```

### View Agent Hierarchy
```sql
SELECT id, agent_type, depth, task_description, status 
FROM agents 
WHERE execution_id='exec_abc123' 
ORDER BY depth, created_at;
```

### View Agent Dependencies
```sql
SELECT e.*, 
       a1.task_description as from_task,
       a2.task_description as to_task
FROM edges e
JOIN agents a1 ON e.from_agent_id = a1.id
JOIN agents a2 ON e.to_agent_id = a2.id
WHERE e.execution_id='exec_abc123';
```

### View Critique Results
```sql
SELECT c.*, a.task_description 
FROM critiques c
JOIN agents a ON c.agent_id = a.id
WHERE a.execution_id='exec_abc123'
ORDER BY c.created_at;
```

### View Tool Executions
```sql
SELECT t.*, a.task_description 
FROM tool_executions t
JOIN agents a ON t.agent_id = a.id
WHERE a.execution_id='exec_abc123';
```

---

## Other Example Use Cases

You can modify `example_use_case.py` to test different scenarios:

### 1. Software Development Domain
```python
execution_payload = {
    "objective": "Analyze this Python codebase for security vulnerabilities and generate a report",
    "domain": "Software Development",
    "config": {"max_recursion_depth": 5}
}
```

### 2. Observability Domain
```python
execution_payload = {
    "objective": "Monitor application logs for the past hour and identify anomalies",
    "domain": "Observability",
    "config": {"max_recursion_depth": 3}
}
```

### 3. Travel Planning Domain (Any Domain!)
```python
execution_payload = {
    "objective": "Book round-trip tickets from NYC to Paris for 2 people, departing June 25, returning July 5",
    "domain": "Travel Planning",
    "config": {"max_recursion_depth": 5}
}
```

### 4. Data Analysis Domain
```python
execution_payload = {
    "objective": "Analyze sales data from Q1 2024 and create executive summary with visualizations",
    "domain": "Data Analysis",
    "config": {"max_recursion_depth": 4}
}
```

### 5. Research Domain
```python
execution_payload = {
    "objective": "Research latest trends in AI safety and compile a 10-page literature review",
    "domain": "Research",
    "config": {"max_recursion_depth": 5}
}
```

---

## Troubleshooting

### No agents created
- Check server logs for errors
- Verify database is writable
- Ensure objective is clear and actionable

### WebSocket disconnects
- Check WEBSOCKET_PING_INTERVAL in .env (default: 30s)
- Server logs will show connection errors
- Try increasing ping timeout in example script

### Agents fail
- Check GEMINI_API_KEY is set (for LLM-based agents)
- Review ToolExecution table for tool errors
- Check agent timeout settings

### Critique rejects outputs
- Agents must include citations (anti-hallucination requirement)
- Confidence must be >= 70%
- Check Critique table for specific failure reasons

---

## Next Steps

After running this example:

1. ✅ Verify backend works end-to-end
2. 📊 Inspect database to see agent hierarchy
3. 🔍 Review tool executions and critique results
4. 🎨 Proceed with frontend development
5. 🚀 Deploy to production

---

## API Reference

For full API documentation, visit:
http://localhost:8000/docs

**Key Endpoints:**
- `POST /api/executions` - Create new execution
- `GET /api/executions/{id}` - Get execution details
- `GET /api/agents/{id}` - Get agent details
- `GET /health` - Health check
- `WS /ws/studio/{id}` - Planning phase WebSocket
- `WS /ws/control-room/{id}` - Execution phase WebSocket
