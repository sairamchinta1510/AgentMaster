# AgentMaster Dual Mode System

AgentMaster supports two distinct operational modes, mirroring a professional software development workflow:

---

## 🎨 Studio Mode (Design/Planning Phase)

**Purpose:** Visualize and approve the agent decomposition plan before execution.

**WebSocket Endpoint:** `/ws/studio/{execution_id}`

**What Happens:**
1. User submits a task objective
2. AgentMaster creates a root Sub-Agent
3. Sub-Agent analyzes complexity and decomposes into child agents
4. **Studio broadcasts events** as the agent hierarchy is built:
   - `agent_created` - New agent added to plan
   - `edge_created` - Dependency added between agents
   - `design_complete` - Planning phase finished

**Use Cases:**
- Review the planned agent hierarchy before execution
- Verify task decomposition is correct
- Understand complexity scoring and agent types
- See dependencies between agents (DAG structure)

**Frontend Integration:**
```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/studio/${executionId}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.event_type === "agent_created") {
    // Render agent node in visualization
    console.log(`Agent planned: ${data.data.agent_type}`);
  }
  
  if (data.event_type === "design_complete") {
    // Show "Approve" button to user
    // User can review plan before starting execution
  }
};
```

**Status:** Execution stays in `status: "planning"` during Studio mode

---

## ⚡ Control Room Mode (Run/Execution Phase)

**Purpose:** Monitor real-time execution of agents and their validation.

**WebSocket Endpoint:** `/ws/control-room/{execution_id}`

**What Happens:**
1. Execution begins (automatically or after user approval)
2. **Control Room broadcasts events** as agents execute:
   - `execution_started` - Run phase begins
   - `agent_started` - Agent begins execution
   - `agent_completed` - Agent finished successfully
   - `agent_failed` - Agent encountered error
   - `critique_round_started` - Validation begins
   - `critique_completed` - Validation verdict
   - `human_review_needed` - Agent needs manual review
   - `execution_completed` - All done!
   - `execution_failed` - Critical error occurred

**Use Cases:**
- Monitor live progress of task execution
- See which agents are currently running
- Track validation (critique) results in real-time
- Identify failed agents immediately
- Watch file creation and tool usage

**Frontend Integration:**
```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/control-room/${executionId}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.event_type === "agent_started") {
    console.log(`Executing: ${data.data.agent_name}`);
    // Show progress spinner
  }
  
  if (data.event_type === "critique_completed") {
    const verdict = data.data.verdict; // "approved" | "rejected" | "needs_human_review"
    console.log(`Validation: ${verdict} (${data.data.confidence}% confidence)`);
  }
  
  if (data.event_type === "execution_completed") {
    // Show success message, display created files
  }
};
```

**Status:** Execution transitions to `status: "running"` then `status: "completed"`

---

## 🔄 Complete Workflow

```
User submits task
     ↓
[STUDIO MODE - Planning]
     ↓
  Planning
  └─ Root Sub-Agent created
  └─ Task decomposition
  └─ Child agents planned
  └─ Dependencies mapped
  └─ Broadcast: design_complete
     ↓
  (Optional: User approval)
     ↓
[CONTROL ROOM MODE - Execution]
     ↓
  Running
  └─ Execute agents in topological order
  └─ Run critique validation
  └─ Retry on failure (max 3x)
  └─ Broadcast progress events
     ↓
  Completed
  └─ Files created
  └─ Results available
```

---

## 📊 Current Implementation Status

| Feature | Studio Mode | Control Room Mode |
|---------|-------------|-------------------|
| WebSocket Endpoint | ✅ `/ws/studio/{id}` | ✅ `/ws/control-room/{id}` |
| Event Broadcasting | ✅ agent_created, edge_created | ✅ All execution events |
| Real-time Updates | ✅ Planning phase | ✅ Execution phase |
| User Approval Gate | ⚠️ Planned (not enforced) | ✅ Auto-starts |
| Frontend UI | ❌ Not built | ❌ Not built |

**Current Behavior:** 
- Studio mode broadcasts planning events
- Control Room **automatically starts execution** after planning
- No manual approval gate between modes (can be added)

---

## 🎯 Example: Using Both Modes

### Terminal 1: Studio (Watch Planning)
```bash
websocat ws://localhost:8000/ws/studio/abc-123-def

# Output:
{"event_type": "agent_created", "data": {"agent_id": "...", "agent_type": "sub_agent"}}
{"event_type": "agent_created", "data": {"agent_id": "...", "agent_type": "atomic_agent"}}
{"event_type": "edge_created", "data": {"from_agent_id": "...", "to_agent_id": "..."}}
{"event_type": "design_complete"}
```

### Terminal 2: Control Room (Watch Execution)
```bash
websocat ws://localhost:8000/ws/control-room/abc-123-def

# Output:
{"event_type": "execution_started"}
{"event_type": "agent_started", "data": {"agent_name": "..."}}
{"event_type": "critique_round_started", "data": {"round": 1}}
{"event_type": "critique_completed", "data": {"verdict": "approved"}}
{"event_type": "agent_completed"}
{"event_type": "execution_completed"}
```

### Using run_task.py (Control Room Only)
```bash
python run_task.py

# Shows:
# - Live execution progress
# - Validation results
# - Final statistics
# - File paths and links
```

---

## 🚀 Future Enhancements

1. **Approval Gate:** Pause between Studio and Control Room for manual approval
2. **Studio Frontend:** Visual graph of planned agent hierarchy
3. **Control Room Frontend:** Live dashboard with progress bars
4. **Plan Editing:** Modify agent plan before execution
5. **Pause/Resume:** Stop execution and resume later
6. **Agent Inspector:** View individual agent inputs/outputs in real-time

---

## 📝 API Response Fields

**Execution Status Values:**
- `planning` - Studio mode active
- `running` - Control Room mode active
- `completed` - Successfully finished
- `failed` - Critical error occurred
- `stopped_by_user` - Manual cancellation

**Agent Status Values:**
- `pending` - Not yet executed
- `running` - Currently executing
- `critique_phase` - Being validated
- `completed` - Finished successfully
- `failed` - Execution error
- `human_review` - Needs manual intervention

---

## 🔗 Related Files

- **Studio WebSocket:** `app/api/websockets/studio.py`
- **Control Room WebSocket:** `app/api/websockets/control_room.py`
- **WebSocket Manager:** `app/services/websocket_manager.py`
- **Execution Manager:** `app/services/execution_manager.py`
- **CLI Tool (Control Room):** `run_task.py`
- **Example (Both Modes):** `example_use_case.py`
