# Backend Validation Guide

## Quick Start

### 1. Start the Backend Server

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

Server will start at: http://localhost:8000

### 2. Run Validation (in a new terminal)

```bash
cd backend_new
python validate_backend.py
```

## Validation Options

### Full Validation (Recommended)
Tests all backend functionality:
```bash
python validate_backend.py
```

**What it tests:**
1. ✅ Health check endpoint
2. ✅ Create execution (POST /api/executions)
3. ✅ Get execution (GET /api/executions/{id})
4. ✅ Studio WebSocket (planning phase)
5. ✅ Control Room WebSocket (execution phase with live agent monitoring)
6. ✅ Database verification (SQLite tables and records)

### Quick Health Check
Just verify server is running:
```bash
python validate_backend.py --quick
```

## Expected Output

```
============================================================
                   AgentMaster Backend Validation                    
============================================================

============================================================
                      1. Health Check                      
============================================================

✓ Server is healthy: {'status': 'healthy', 'service': 'agentmaster'}

============================================================
                   2. Create Execution                    
============================================================

✓ Execution created: abc-123-def
ℹ Status: planning
ℹ Objective: Echo 'Hello AgentMaster' to test the system
ℹ Domain: Testing
ℹ Root agent: agent_001

============================================================
                   3. Get Execution                    
============================================================

✓ Retrieved execution: abc-123-def
ℹ Status: planning
ℹ Created: 2026-06-21T10:30:00Z

============================================================
          4. Studio WebSocket (Planning Phase)          
============================================================

ℹ Connecting to: ws://localhost:8000/ws/studio/abc-123-def
✓ Connected to Studio WebSocket
ℹ Event: agent_created
ℹ Event: edge_created
✓ Studio WebSocket test complete

============================================================
       5. Control Room WebSocket (Execution Phase)       
============================================================

ℹ Connecting to: ws://localhost:8000/ws/control-room/abc-123-def
✓ Connected to Control Room WebSocket
ℹ Monitoring execution... (max 30 seconds)
ℹ Event: execution_started
ℹ Event: agent_started
ℹ   → Agent started: Echo 'Hello AgentMaster' to test the system
ℹ Event: agent_completed
✓   → Agent completed: Echo 'Hello AgentMaster' to test the system
ℹ Event: critique_completed
ℹ   → Critique verdict: approved
ℹ Event: execution_completed
✓ Execution completed!

ℹ Execution Summary:
ℹ   Events received: 15
ℹ   Agents completed: 3

============================================================
                6. Database Verification                
============================================================

✓ Database file exists: /Users/schinta/AgentMaster/backend_new/agentmaster.db
✓ Table 'executions': 5 records
✓ Table 'agents': 12 records
✓ Table 'edges': 8 records
✓ Table 'critiques': 9 records
✓ Table 'tool_executions': 3 records
✓ Table 'agent_templates': 0 records

============================================================
                  Validation Summary                  
============================================================

PASS - health
PASS - create_execution
PASS - get_execution
PASS - studio_ws
PASS - control_room_ws
PASS - database

Overall: 6/6 tests passed

✓ Backend is fully functional and ready for frontend integration!
```

## Manual Testing with Swagger UI

Visit http://localhost:8000/docs for interactive API documentation.

### Test Flow:

1. **Create Execution**
   - POST /api/executions
   - Body:
   ```json
   {
     "objective": "Test the system with a simple echo command",
     "domain": "Testing",
     "config": {
       "max_recursion_depth": 5
     }
   }
   ```

2. **Get Execution**
   - GET /api/executions/{id}
   - Use the ID from step 1

3. **Get Agent Details**
   - GET /api/agents/{agent_id}
   - Use root_agent_id from execution

## Manual Testing with WebSocket Client

You can also test WebSockets manually using `websocat` or browser JavaScript:

```bash
# Install websocat
brew install websocat

# Connect to Studio
websocat ws://localhost:8000/ws/studio/{execution_id}

# Connect to Control Room
websocat ws://localhost:8000/ws/control-room/{execution_id}
```

## Troubleshooting

### "Cannot connect to server"
- Make sure backend is running: `uvicorn app.main:app --reload`
- Check the server is on port 8000
- Look for errors in the server logs

### "Database not found"
- The database is auto-created on first run
- If missing, restart the server to initialize it

### "Tests timeout"
- Increase timeout in validate_backend.py
- Check server logs for errors
- Verify GEMINI_API_KEY is set in .env (for LLM-based agents)

### "No events received"
- This is OK if planning completed before WebSocket connected
- Try creating a new execution and connecting faster

## Next Steps

Once validation passes:
1. ✅ Backend is production-ready
2. 📱 Proceed with frontend implementation
3. 🚀 Set up deployment pipeline

## Advanced: Database Inspection

```bash
cd backend_new
sqlite3 agentmaster.db

# View all tables
.tables

# View executions
SELECT * FROM executions;

# View agents
SELECT id, agent_type, depth, status FROM agents;

# Exit
.quit
```

## Environment Variables

Create `.env` file in `backend_new/`:

```env
DATABASE_URL=sqlite:///./agentmaster.db
GEMINI_API_KEY=your_actual_gemini_api_key
LOG_LEVEL=info
MAX_RECURSION_DEPTH=5
MAX_AGENT_TIMEOUT=300
WEBSOCKET_PING_INTERVAL=30
```

**Note:** GEMINI_API_KEY is optional for basic testing. LLM-based agents will use stub responses without it.
