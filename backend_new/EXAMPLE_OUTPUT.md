# Example: Enhanced run_task.py Output

This shows what you'll see when running a task with the enhanced statistics and file detection.

---

## Running the Task

```bash
cd /Users/schinta/AgentMaster/backend_new
source venv/bin/activate
python run_task.py
```

---

## Sample Output

```
======================================================================
                      AGENTMASTER - Run New Task                      
======================================================================

Examples of tasks you can run:
  • Create a technical document or guide
  • Write a blog post or article
  • Generate code examples
  • Create training materials
  • Write documentation

Enter your objective:
> Create 10 exercises for Product Managers to learn Claude automation

Enter domain (or press Enter for 'General'):
  Examples: Content Generation, Documentation, Software Development
> Training Materials

Max recursion depth (1-5, default 5):
> 3

======================================================================
                        Submitting Task                        
======================================================================

Objective: Create 10 exercises for Product Managers to learn Claude automation
Domain: Training Materials
Max Depth: 3

✓ Task submitted!
Execution ID: 573cd44f-5648-43a1-b748-a6bec719cf41

Connecting to execution monitor...
✓ Connected

✅ Execution started - agents are being created and executed...

  📝 Planned: 🔷 sub_agent - [Training Materials] Create 10 exercises...
  📝 Planned: ⚡ atomic_agent - Handle simple part: [Training Materials]...

⚡ Executing: [Training Materials] Create 10 exercises for Product Managers...
  → Validating output (Round 1)...
  → Validating output (Round 2)...
  → Validating output (Round 3)...
  ✓ Validation: approved (95% confidence)
✅ Completed: [Training Materials] Create 10 exercises...

⚡ Executing: Handle simple part: [Training Materials] Create 10 exercises...
  → Validating output (Round 1)...
  → Validating output (Round 2)...
  → Validating output (Round 3)...
  ✓ Validation: approved (95% confidence)
✅ Completed: Handle simple part...

🎉 EXECUTION COMPLETED!

======================================================================
                        Execution Summary                        
======================================================================

Execution ID: 573cd44f-5648-43a1-b748-a6bec719cf41
Status: completed
Duration: 62.3 seconds

Agent Statistics:
  Total Agents Planned: 2
  └─ Sub-Agents (decomposition): 1
  └─ Atomic Agents (execution): 1
  Completed: 2
  Failed: 0

Validation Results:
  ✅ Approved: 2
  ❌ Rejected: 0

Created Files:

  📄 practical_exercises_product_20260621_111231.md
     Size: 49.2 KB
     Path: /Users/schinta/AgentMaster/backend_new/practical_exercises_product_20260621_111231.md
     Link: file:///Users/schinta/AgentMaster/backend_new/practical_exercises_product_20260621_111231.md

  📄 handle_simple_part_20260621_111337.md
     Size: 50.1 KB
     Path: /Users/schinta/AgentMaster/backend_new/handle_simple_part_20260621_111337.md
     Link: file:///Users/schinta/AgentMaster/backend_new/handle_simple_part_20260621_111337.md

API Links:
  Execution Details: http://localhost:8000/api/executions/573cd44f-5648-43a1-b748-a6bec719cf41
  API Documentation: http://localhost:8000/docs
  Studio (Design Mode): ws://localhost:8000/ws/studio/573cd44f-5648-43a1-b748-a6bec719cf41
  Control Room (Run Mode): ws://localhost:8000/ws/control-room/573cd44f-5648-43a1-b748-a6bec719cf41
```

---

## What You Get

### ✅ Real-Time Progress Updates
- See each agent being planned
- Watch execution in real-time
- Track validation rounds
- Know when tasks complete

### 📊 Detailed Statistics
- **Agent Breakdown:** Sub-Agents vs Atomic Agents
- **Success Rate:** Completed vs Failed
- **Validation Stats:** Approved vs Rejected critiques
- **Timing:** Total execution duration

### 📄 File Information
- **Automatic Detection:** Finds files created in last 5 minutes
- **Full Paths:** Absolute paths to documents
- **Clickable Links:** `file://` URLs you can click in terminal
- **File Sizes:** Know how large each document is

### 🔗 API Access
- **Execution Details API:** Get full JSON response
- **Interactive Docs:** Swagger UI at `/docs`
- **WebSocket URLs:** Connect to Studio or Control Room modes

---

## Two Modes Explained

### 🎨 Studio Mode (Design/Planning)
**Purpose:** Review the agent plan before execution

**When to use:**
- You want to approve the decomposition strategy
- Need to verify complexity scoring
- Want to see the agent hierarchy upfront

**WebSocket:** `ws://localhost:8000/ws/studio/{execution_id}`

**Events:**
- `agent_created` - New agent planned
- `edge_created` - Dependency added
- `design_complete` - Ready for execution

### ⚡ Control Room Mode (Run/Execution)
**Purpose:** Monitor real-time execution

**When to use:**
- Watch tasks being executed
- See validation results
- Track file creation
- Monitor for failures

**WebSocket:** `ws://localhost:8000/ws/control-room/{execution_id}`

**Events:**
- `execution_started` - Run begins
- `agent_started` - Agent executing
- `critique_completed` - Validation done
- `execution_completed` - All finished

**Currently:** Control Room auto-starts after Studio planning completes.

---

## Key Benefits

1. **Transparency:** See exactly what's happening
2. **Traceability:** Full execution ID for debugging
3. **Convenience:** Direct file links to open documents
4. **Insights:** Understand agent hierarchy and performance
5. **Integration Ready:** WebSocket URLs for custom UIs

---

## Next Steps

- Click the `file://` links to open created documents
- Use the API URLs to inspect execution details
- Connect to WebSockets for custom monitoring
- Read `DUAL_MODE_GUIDE.md` for frontend integration
