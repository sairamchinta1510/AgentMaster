# AgentMaster - Cached Results Debugging Guide

## Problem

When running a pipeline multiple times, the system returns cached/previous results instead of executing fresh runs.

## Root Cause

The system has a two-phase architecture:

1. **DESIGN Phase** (`/ws/design/{pipeline_id}`):
   - Generates agent blueprint
   - Runs critique loops
   - **Saves blueprint to database** (Line 304-308 in `app/api/ws_design.py`)

2. **RUN Phase** (`/ws/run/{run_id}`):
   - Loads blueprint from database (Line 208 in `app/api/ws_run.py`)
   - Executes the cached blueprint
   - **Does NOT regenerate agents**

### The Bug

File: `backend/app/api/ws_run.py:208-209`

```python
blueprint = pipeline.blueprint or {}  # <- Uses cached blueprint!
agents = blueprint.get("agents", [])
```

Every run reuses the same blueprint stored during the DESIGN phase.

## Solutions

### Solution 1: Clear Blueprint Before Each Run (Quick Fix)

Add an API endpoint to clear the cached blueprint:

**File:** `backend/app/api/routes/pipelines.py`

Add this endpoint:

```python
@router.post("/{pipeline_id}/clear-blueprint", response_model=Pipeline)
def clear_blueprint(pipeline_id: str, db: Session = Depends(get_db)):
    """Clear the cached blueprint to force regeneration on next design."""
    row = db.query(PipelineORM).filter(PipelineORM.id == pipeline_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    row.blueprint = {}
    row.input_schema = []
    db.commit()
    db.refresh(row)
    backup_to_gcs()
    return _orm_to_pipeline(row)
```

**Usage:**
```bash
curl -X POST https://agentmaster-ouabviezcq-ew.a.run.app/api/pipelines/{pipeline_id}/clear-blueprint
```

Then redesign and run.

### Solution 2: Add "Force Redesign" Flag (Better)

Modify the run creation to optionally force a redesign:

**File:** `backend/app/api/routes/runs.py`

```python
class CreateRunRequest(BaseModel):
    pipeline_id: str
    inputs: dict = Field(default_factory=dict)
    force_redesign: bool = False  # <- Add this

@router.post("", status_code=201, response_model=Run)
def create_run(req: CreateRunRequest, db: Session = Depends(get_db)):
    pipeline = db.query(PipelineORM).filter(PipelineORM.id == req.pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    # Clear blueprint if force_redesign is true
    if req.force_redesign:
        pipeline.blueprint = {}
        pipeline.input_schema = []
        db.commit()
    
    run_id = str(uuid.uuid4())
    # ... rest of code
```

### Solution 3: Separate Pipeline Templates from Runs (Architectural Fix)

Create a new model for "pipeline templates" vs "executions":

- **PipelineTemplate**: Stores the objective and configuration
- **PipelineExecution**: Each execution gets its own blueprint

This requires refactoring but is the cleanest long-term solution.

## Workaround (No Code Changes)

1. Delete the pipeline
2. Create a new pipeline with the same objective
3. Run the design phase
4. Execute the run

## Testing the Fix

After implementing any solution:

1. Create a pipeline: `POST /api/pipelines` with objective
2. Run design: Connect to `/ws/design/{pipeline_id}`
3. Create first run: `POST /api/runs`
4. Execute first run: Connect to `/ws/run/{run_id}`
5. **Clear blueprint** (using chosen solution)
6. Run design again
7. Create second run
8. Execute second run
9. Verify different agents/results

## Files Involved

- `backend/app/api/ws_design.py:304-308` - Saves blueprint
- `backend/app/api/ws_run.py:208-209` - Loads cached blueprint
- `backend/app/api/routes/pipelines.py` - Pipeline CRUD
- `backend/app/api/routes/runs.py` - Run creation
- `backend/app/models/pipeline.py` - Pipeline model with blueprint field

## Database Schema

```sql
-- pipelines table
CREATE TABLE pipelines (
    id VARCHAR PRIMARY KEY,
    objective VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    input_schema JSON DEFAULT '[]',
    blueprint JSON DEFAULT '{}',  -- <- This is cached!
    default_inputs JSON DEFAULT '{}',
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

The `blueprint` column stores the entire agent design and is reused across runs.
