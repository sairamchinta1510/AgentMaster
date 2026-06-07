# Auto-Decomposition of Non-Atomic Agents

**Date:** 2026-06-07  
**Status:** Approved  

---

## Problem

When the critique agent identifies an atomicity violation (an agent performs more than one distinct action), the current system has no recovery path beyond rewording the same agent up to 5 times. The `suggested_new_agents` field in `CritiqueResult` is populated by the LLM but never read or acted upon. The pipeline stalls at `USER_ESCALATED` even though the correct fix — splitting into two smaller agents — is already known.

---

## Goal

When a critique detects an irrecoverable atomicity violation, the system automatically:
1. Decomposes the offending agent into N atomic sub-agents (as suggested by the critique LLM)
2. Produces and critiques each sub-agent independently
3. Injects the approved sub-agents into the DAG in place of the original

The user should never see `USER_ESCALATED` solely because an agent description implied two actions.

---

## Decomposition Trigger (Option B — Revise Once, Then Decompose)

- **Iteration 1:** critique finds atomicity issue → producer revises the agent (existing behaviour, unchanged)
- **Iteration 2+:** critique still finds atomicity issue AND `suggested_new_agents` is non-empty → **trigger decomposition**
- If `suggested_new_agents` is empty despite an atomicity issue, continue the existing escalation path (the critique LLM failed to suggest a split; treat as normal revision)

This avoids prematurely splitting agents whose descriptions can be fixed by rewording, while ensuring real multi-action agents are correctly decomposed.

---

## Architecture

### 1. Critique Prompt (`prompts/critique.py`)

Add explicit structure and instruction to `suggested_new_agents`:

```json
"suggested_new_agents": [
  {
    "agent_name": "DescriptiveName",
    "description": "Single atomic action this agent performs",
    "input_schema": { "field": { "type": "string", "required": true, "description": "..." } },
    "output_schema": { "field": { "type": "string", "description": "..." } }
  }
]
```

Add instruction: **whenever an atomicity issue is raised, `suggested_new_agents` MUST be populated with the complete decomposition** — one entry per atomic sub-agent. An atomicity issue with an empty `suggested_new_agents` is invalid.

### 2. `run_critique_loop` (`agents/agent_critique.py`)

**Signature change:**
```python
async def run_critique_loop(...) -> tuple[CritiqueResult, list[AtomicAgent], int]:
```

**New logic after iteration 1:**
```
if iteration >= 2
   AND any issue has category == "atomicity"
   AND result.suggested_new_agents is non-empty:
     → call decompose_agent(original, suggested_new_agents, producer, critique, phase)
     → return (final_critique, decomposed_agents, iteration)
```

**`decompose_agent` helper (new, same file):**
- For each entry in `suggested_new_agents`:
  - Assign a deterministic `agent_id` (`{original_id}_part_{n}`)
  - Call `producer.produce()` to generate full spec
  - Run a fresh `run_critique_loop` (max 5 iterations)
- Return all approved sub-agents as `list[AtomicAgent]`

### 3. DAG Surgery (`api/ws_design.py`)

After `run_critique_loop` returns, when `len(result_agents) > 1` (decomposition occurred):

- Remove the original DAG node
- Add one new node per sub-agent
- Wire in series: `predecessors_of_original → sub_agent[0] → … → sub_agent[N-1] → successors_of_original`
- Emit `DAG_UPDATED` WebSocket event with the revised DAG

When `len(result_agents) == 1` (no decomposition), behaviour is unchanged.

### 4. Caller Updates

All three callers that call `run_critique_loop` must handle `list[AtomicAgent]`:

| File | Change |
|------|--------|
| `api/ws_design.py` | Loop over returned agents; call DAG surgery helper |
| `api/ws_extend.py` | Loop over returned agents; append all to `approved_new` |
| `api/websocket.py` | Loop over returned agents; increment `approved_count` for each |

---

## Data Flow

```
Critique iteration N (N≥2)
  └─ atomicity issue + suggested_new_agents populated?
       ├─ NO  → revise (existing path)
       └─ YES → decompose_agent()
                  ├─ produce sub_agent_1 → critique loop → approved
                  ├─ produce sub_agent_2 → critique loop → approved
                  └─ return [sub_agent_1, sub_agent_2]
                DAG: remove original node, insert [sub_agent_1, sub_agent_2] in series
                WS: emit DAG_UPDATED
```

---

## Error Handling

- If a sub-agent's critique loop also fails atomicity → it recurses (depth limited to 1 level of decomposition to avoid infinite loops — enforced by passing `allow_decompose=False` to nested `run_critique_loop` calls)
- If `decompose_agent` produces zero approved agents → fall back to `USER_ESCALATED` on the original agent

---

## Tests

- `test_critique_loop.py`: add case where mock critique returns atomicity issue + `suggested_new_agents` on iteration 2 → assert returned list has N agents
- `test_critique_loop.py`: add case where `suggested_new_agents` is empty despite atomicity issue → assert single-agent escalation path unchanged
