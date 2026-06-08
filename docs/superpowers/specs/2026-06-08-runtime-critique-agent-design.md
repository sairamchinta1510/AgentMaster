# Runtime Critique Agent — Design Spec
**Date:** 2026-06-08  
**Status:** Approved

---

## Problem

Agents in a pipeline can produce incorrect, incomplete, or non-industry-standard outputs without any validation before the next agent runs. Current heuristics (regex checks, retry-on-error) are fragile and miss semantic issues like reading output-schema fields as input env vars, or using a non-standard approach for the task domain.

---

## Solution: Independent Critique Agent Node

A `Critique` node is a first-class agent type in the pipeline DAG. The pipeline designer explicitly places it after agents they want validated. At runtime it acts as a **domain-expert LLM reviewer** — it validates the preceding agent(s) against industry best standards for their specific task, and sends fix instructions back to the agent if issues are found.

---

## Architecture

```
Designer builds pipeline:
  CloneRepo → IdentifyLogStorage → [Critique] → AnalyzeStructure

At runtime:
  1. CloneRepo runs normally
  2. IdentifyLogStorage runs → produces output
  3. Critique node fires:
       a. LLM becomes domain expert for IdentifyLogStorage's task
       b. Evaluates output against logging/observability industry standards
       c. APPROVED → pipeline moves forward
       d. NEEDS_FIX → sends instructions back to IdentifyLogStorage → re-runs
       e. Repeats: min 3 iterations (clean run), max 5 (on error)
  4. AnalyzeStructure runs with validated, quality output
```

---

## Critique Node Definition

```json
{
  "agent_id": "critique_001",
  "agent_name": "CritiqueLogStorageIdentification",
  "agent_type": "critique",
  "description": "Validates log storage identification against observability industry standards",
  "depends_on": ["identify_log_storage"],
  "critique_config": {
    "min_iterations": 3,
    "max_iterations_on_error": 5
  }
}
```

- `agent_type: "critique"` — distinguished from normal `"task"` agents
- `depends_on` — the agents this critique validates (those agents are re-run if needed)
- `description` — used to specialise the LLM critic prompt

---

## Critique LLM Prompt

The Critique LLM is primed as a domain expert based on the target agent's name and description:

```
You are a world-class expert in <target_agent_description_domain>.

Review the following agent's execution against industry best standards:

Agent: <name>
Task: <description>
Input Schema: <schema>
Output Schema: <schema>
Inputs Used: <actual inputs>
Code Executed: <code>
Output Produced: <output>
Errors/Warnings: <stderr>

Evaluate:
1. Are inputs read correctly? (not reading output-schema fields as env vars)
2. Does the output fulfil the agent's stated purpose completely?
3. Is the approach industry-standard for this type of task?
4. Are there security, reliability, or correctness issues?
5. Is the output meaningful, complete, and actionable?

Return ONLY JSON:
{
  "verdict": "APPROVED" | "NEEDS_FIX",
  "quality_score": 1-10,
  "issues": ["specific issue 1", ...],
  "fix_instructions": "Precise instructions for the agent to fix its approach"
}
```

---

## Runtime Behaviour

### Normal flow (no errors):
- Runs **minimum 3 critique iterations** even if first passes
- Each iteration: agent re-executes → critique evaluates
- After min 3 with `APPROVED` → pipeline proceeds

### Error flow:
- On `NEEDS_FIX` or execution failure: up to **5 iterations**
- Each retry: critique's `fix_instructions` + web-search context injected into re-plan
- After 5 failures: Critique node marks itself `failed`, pipeline uses cascade-skip

### State reporting:
- Each critique iteration emits a `CRITIQUE_ITERATION` WebSocket event
- Final result includes `{verdict, iterations, quality_score, issues}`

---

## Components

| File | Role |
|------|------|
| `backend/app/agents/runtime_critique.py` | `CritiqueAgent` class — LLM-based domain-expert evaluator |
| `backend/app/api/ws_run.py` | Detect `agent_type=critique`, run critique loop |
| `backend/app/models/agent.py` | Add `agent_type` field, `CritiqueConfig` model |
| `backend/app/prompts/critique_runtime.py` | Critique LLM system prompt |
| `backend/tests/test_runtime_critique.py` | TDD tests |

---

## What Does NOT Change

- Normal task agents (`agent_type: "task"`) are unchanged
- The existing design-time critique loop (blueprint generation) is unchanged
- The static `code_reviewer.py` pre-checks remain as a fast pre-filter

---

## Success Criteria

1. A Critique node in the pipeline validates its predecessor's output via LLM
2. `NEEDS_FIX` causes the predecessor to re-run with fix instructions (not the critique fixing the code)
3. Min 3 iterations on clean run, max 5 on error
4. Critique LLM is domain-specific (specialised by agent description)
5. All existing 66 tests continue passing
6. 10+ new tests for critique loop behaviour
