# Auto-Decomposition of Non-Atomic Agents — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When the critique loop detects a persistent atomicity violation, automatically decompose the offending agent into N atomic sub-agents, produce and critique each, then inject them into the DAG in place of the original.

**Architecture:** `run_critique_loop` gains a decomposition path triggered on iteration ≥ 2 when atomicity issues persist and `suggested_new_agents` is populated. It returns `list[AtomicAgent]` instead of a single agent. All three WS callers are updated to handle the list, and `ws_design.py` performs DAG surgery to replace the original node with N nodes wired in series.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, pytest-asyncio, unittest.mock

---

## File Map

| Action | Path |
|--------|------|
| Modify | `backend/app/prompts/critique.py` |
| Modify | `backend/app/agents/agent_critique.py` |
| Modify | `backend/app/api/ws_design.py` |
| Modify | `backend/app/api/ws_extend.py` |
| Modify | `backend/app/api/websocket.py` |
| Modify | `backend/tests/test_critique_loop.py` |

---

### Task 1: Update critique prompt — structure `suggested_new_agents`

**Files:**
- Modify: `backend/app/prompts/critique.py`

The critique LLM currently returns `"suggested_new_agents": []` with no guidance. We need it to populate structured specs whenever it raises an atomicity issue so the producer can act on them.

- [ ] **Step 1: Update `AGENT_CRITIQUE_SYSTEM_PROMPT` in `critique.py`**

Replace the `"suggested_new_agents": []` line in the OUTPUT FORMAT section and add a rule below `## ABSOLUTE RULE`:

```python
# In the OUTPUT FORMAT JSON block, replace:
#   "suggested_new_agents": [],
# with:
      "suggested_new_agents": [
        {
          "agent_name": "DescriptiveName",
          "description": "Single atomic action this sub-agent performs",
          "input_schema": {"field": {"type": "string", "required": true, "description": "..."}},
          "output_schema": {"field": {"type": "string", "description": "..."}}
        }
      ],
```

Add this rule directly after the existing `## ABSOLUTE RULE` block:

```
## DECOMPOSITION RULE
Whenever you raise an atomicity issue (category == "atomicity"), you MUST populate
suggested_new_agents with the complete decomposition — one entry per atomic sub-agent.
An atomicity issue with an empty suggested_new_agents list is invalid and will be rejected.
Each sub-agent entry must contain: agent_name, description, input_schema, output_schema.
```

- [ ] **Step 2: Commit**

```bash
cd backend
git add app/prompts/critique.py
git commit -m "feat: require structured suggested_new_agents on atomicity issues"
```

---

### Task 2: Add `decompose_agent` helper and update `run_critique_loop` return type

**Files:**
- Modify: `backend/app/agents/agent_critique.py`
- Test: `backend/tests/test_critique_loop.py`

- [ ] **Step 1: Write the failing tests first**

Add to `backend/tests/test_critique_loop.py`:

```python
@pytest.mark.asyncio
async def test_critique_loop_decomposes_on_persistent_atomicity():
    """On iteration 2+, atomicity issue + suggested_new_agents → decompose into 2 agents."""
    agent = AtomicAgent(
        agent_id="orig",
        agent_name="MultiAgent",
        session_id="s1",
        description="Clones repo and analyzes logs",
    )

    atomicity_issue = {
        "issue_id": "ISS-001",
        "severity": "critical",
        "category": "atomicity",
        "description": "Does two things",
        "impact": "Violates Law 1",
        "recommendation": "Split into two agents",
        "effort_estimate": "medium",
        "auto_fixable": True,
    }

    # Both iterations return the atomicity violation with suggested decomposition
    critique_with_decomp = {
        "critique_id": "orig_critique_iter_1",
        "target_agent": "orig",
        "target_agent_name": "MultiAgent",
        "phase": "design_time",
        "iteration": 1,
        "max_iterations": 5,
        "verdict": "NEEDS_REVISION",
        "quality_score": 3.0,
        "errors_remaining": 1,
        "issues": [atomicity_issue],
        "approved_aspects": [],
        "improvements_made_this_iteration": [],
        "remaining_errors": ["atomicity"],
        "suggested_new_agents": [
            {
                "agent_name": "CloneRepoAgent",
                "description": "Clones a git repository to a local path",
                "input_schema": {"repo_url": {"type": "string", "required": True, "description": "URL"}},
                "output_schema": {"repo_path": {"type": "string", "description": "Local path"}},
            },
            {
                "agent_name": "AnalyzeLogsAgent",
                "description": "Analyzes log files in a given directory",
                "input_schema": {"repo_path": {"type": "string", "required": True, "description": "Path"}},
                "output_schema": {"log_summary": {"type": "string", "description": "Summary"}},
            },
        ],
        "missing_user_inputs": [],
    }

    sub_agent_1 = AtomicAgent(
        agent_id="orig_part_1",
        agent_name="CloneRepoAgent",
        session_id="s1",
        description="Clones a git repository to a local path",
    )
    sub_agent_2 = AtomicAgent(
        agent_id="orig_part_2",
        agent_name="AnalyzeLogsAgent",
        session_id="s1",
        description="Analyzes log files in a given directory",
    )

    approved_response = {
        "critique_id": "orig_part_1_critique_iter_1",
        "target_agent": "orig_part_1",
        "target_agent_name": "CloneRepoAgent",
        "phase": "design_time",
        "iteration": 1,
        "max_iterations": 5,
        "verdict": "APPROVED",
        "quality_score": 9.0,
        "errors_remaining": 0,
        "issues": [],
        "approved_aspects": ["Atomic"],
        "improvements_made_this_iteration": [],
        "remaining_errors": [],
        "suggested_new_agents": [],
        "missing_user_inputs": [],
    }

    critique_agent = AgentCritiqueAgent(api_key="fake")
    producer_agent = MagicMock()
    producer_agent.revise = AsyncMock(return_value=agent)
    producer_agent.produce = AsyncMock(side_effect=[sub_agent_1, sub_agent_2])

    with patch.object(critique_agent, "_call_llm", new_callable=AsyncMock, return_value=critique_with_decomp):
        # Sub-agent critiques approve immediately
        with patch("app.agents.agent_critique.AgentCritiqueAgent") as MockCritique:
            inner_critique = MockCritique.return_value
            inner_critique._call_llm = AsyncMock(return_value=approved_response)
            result, agents, iterations = await run_critique_loop(
                agent, critique_agent, producer_agent, phase="design_time"
            )

    assert len(agents) == 2
    assert agents[0].agent_id == "orig_part_1"
    assert agents[1].agent_id == "orig_part_2"


@pytest.mark.asyncio
async def test_critique_loop_no_decomp_when_suggested_agents_empty():
    """Atomicity issue with empty suggested_new_agents → escalation, NOT decomposition."""
    agent = AtomicAgent(
        agent_id="a_esc",
        agent_name="EscalatedAgent",
        session_id="s1",
        description="Does too much but LLM gave no suggestions",
    )
    atomicity_no_suggestions = {
        "critique_id": "a_esc_critique_iter_1",
        "target_agent": "a_esc",
        "target_agent_name": "EscalatedAgent",
        "phase": "design_time",
        "iteration": 1,
        "max_iterations": 5,
        "verdict": "NEEDS_REVISION",
        "quality_score": 2.0,
        "errors_remaining": 1,
        "issues": [
            {
                "issue_id": "ISS-001",
                "severity": "critical",
                "category": "atomicity",
                "description": "Does two things",
                "impact": "Bad",
                "recommendation": "Split",
                "effort_estimate": "medium",
                "auto_fixable": False,
            }
        ],
        "approved_aspects": [],
        "improvements_made_this_iteration": [],
        "remaining_errors": ["atomicity"],
        "suggested_new_agents": [],   # empty — no decomp should happen
        "missing_user_inputs": [],
    }
    critique_agent = AgentCritiqueAgent(api_key="fake")
    producer_agent = MagicMock()
    producer_agent.revise = AsyncMock(return_value=agent)

    with patch.object(critique_agent, "_call_llm", new_callable=AsyncMock, return_value=atomicity_no_suggestions):
        result, agents, iterations = await run_critique_loop(
            agent, critique_agent, producer_agent, phase="design_time"
        )

    assert len(agents) == 1          # single agent returned, not decomposed
    assert iterations == 5           # ran all 5 iterations


@pytest.mark.asyncio
async def test_critique_loop_single_agent_return_unchanged_on_approval():
    """Existing approval path still returns list of 1 agent (not a bare AtomicAgent)."""
    agent = AtomicAgent(
        agent_id="good",
        agent_name="GoodAgent",
        session_id="s1",
        description="Does exactly one thing",
    )
    approved = {
        "critique_id": "good_critique_iter_1",
        "target_agent": "good",
        "target_agent_name": "GoodAgent",
        "phase": "design_time",
        "iteration": 1,
        "max_iterations": 5,
        "verdict": "APPROVED",
        "quality_score": 9.0,
        "errors_remaining": 0,
        "issues": [],
        "approved_aspects": [],
        "improvements_made_this_iteration": [],
        "remaining_errors": [],
        "suggested_new_agents": [],
        "missing_user_inputs": [],
    }
    critique_agent = AgentCritiqueAgent(api_key="fake")
    producer_agent = MagicMock()
    producer_agent.revise = AsyncMock(return_value=agent)

    with patch.object(critique_agent, "_call_llm", new_callable=AsyncMock, return_value=approved):
        result, agents, iterations = await run_critique_loop(
            agent, critique_agent, producer_agent, phase="design_time"
        )

    assert len(agents) == 1
    assert agents[0].agent_id == "good"
    assert result.verdict == CritiqueVerdict.APPROVED
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend
.venv\Scripts\python.exe -m pytest tests/test_critique_loop.py -v
```

Expected: new tests fail with `TypeError` (wrong return type) or `AssertionError`.

- [ ] **Step 3: Add `decompose_agent` helper to `agent_critique.py`**

Add this function after `run_critique_loop` in `backend/app/agents/agent_critique.py`:

```python
async def decompose_agent(
    original: "AtomicAgent",
    suggested: list[dict],
    producer_agent,
    critique_agent: "AgentCritiqueAgent",
    phase: str,
    on_event=None,
) -> list["AtomicAgent"]:
    """Produce and critique each suggested sub-agent, returning all approved ones.

    Sub-agent critique loops are run with allow_decompose=False to prevent
    infinite recursion — sub-agents cannot themselves be decomposed further.
    """
    results: list[AtomicAgent] = []
    for idx, spec in enumerate(suggested, 1):
        sub_id = f"{original.agent_id}_part_{idx}"
        full_spec = {
            "agent_id": sub_id,
            "agent_name": spec.get("agent_name", f"SubAgent{idx}"),
            "description": spec.get("description", ""),
            "input_schema": spec.get("input_schema", {}),
            "output_schema": spec.get("output_schema", {}),
            "depends_on": [],
            "timeout_seconds": 60,
        }
        if on_event:
            await on_event("PHASE_UPDATE", {
                "phase": "DECOMPOSING",
                "message": f"Decomposing into sub-agent {idx}/{len(suggested)}: {full_spec['agent_name']}…",
            })
        sub_agent = await producer_agent.produce(
            full_spec, phase, original.session_id, on_event=on_event
        )
        _result, approved, _iters = await run_critique_loop(
            sub_agent, critique_agent, producer_agent, phase,
            on_event=on_event, allow_decompose=False,
        )
        results.extend(approved)
    return results
```

- [ ] **Step 4: Update `run_critique_loop` signature and return type**

Replace the existing `run_critique_loop` function signature and body in `backend/app/agents/agent_critique.py`:

```python
async def run_critique_loop(
    agent: AtomicAgent,
    critique_agent: AgentCritiqueAgent,
    producer_agent,
    phase: str,
    max_iterations: int = 5,
    on_event=None,
    allow_decompose: bool = True,
) -> tuple[CritiqueResult, list[AtomicAgent], int]:
    """Run the up-to-5-iteration critique loop.

    Returns (final_result, list[AtomicAgent], iterations_used).
    Normally returns a list of 1 agent. If an atomicity violation persists
    on iteration 2+ and suggested_new_agents is populated, decomposes the
    agent and returns N sub-agents instead. allow_decompose=False prevents
    infinite recursion in nested calls.
    """
    previous_issues: list[dict] = []
    final_result: CritiqueResult | None = None

    for iteration in range(1, max_iterations + 1):
        if on_event:
            await on_event("PHASE_UPDATE", {
                "phase": f"DESIGN_CRITIQUE_{iteration}",
                "message": f"Critique round {iteration}/5 — calling LLM to review {agent.agent_name}…",
            })
        result = await critique_agent.critique(
            agent, phase, iteration, previous_issues or None, on_event=on_event
        )
        agent.critique_iterations = iteration
        agent.critique_history.append(result)
        final_result = result

        if result.verdict == CritiqueVerdict.APPROVED:
            agent.quality_score = result.quality_score
            if on_event:
                await on_event("PHASE_UPDATE", {
                    "phase": "APPROVED",
                    "message": f"{agent.agent_name} approved ★{result.quality_score}/10 after {iteration} round(s)",
                })
            return result, [agent], iteration

        # Check for decomposable atomicity violation (only from iteration 2 onwards)
        has_atomicity_issue = any(i.category == "atomicity" for i in result.issues)
        if (
            allow_decompose
            and iteration >= 2
            and has_atomicity_issue
            and result.suggested_new_agents
        ):
            if on_event:
                await on_event("PHASE_UPDATE", {
                    "phase": "DECOMPOSING",
                    "message": (
                        f"{agent.agent_name} has persistent atomicity violation — "
                        f"decomposing into {len(result.suggested_new_agents)} sub-agent(s)…"
                    ),
                })
            sub_agents = await decompose_agent(
                agent, result.suggested_new_agents, producer_agent,
                critique_agent, phase, on_event=on_event,
            )
            if sub_agents:
                return result, sub_agents, iteration

        previous_issues = [i.model_dump() for i in result.issues]
        if iteration < max_iterations:
            if on_event:
                await on_event("PHASE_UPDATE", {
                    "phase": "REVISING_SPEC",
                    "message": f"Auto-fixing {len(result.issues)} issue(s) in {agent.agent_name} — calling LLM…",
                })
            agent = await producer_agent.revise(agent, previous_issues, phase, on_event=on_event)

    # After max_iterations — escalate
    assert final_result is not None
    if final_result.errors_remaining > 0:
        final_result.verdict = CritiqueVerdict.ESCALATE_AUTO_FIX

    return final_result, [agent], max_iterations
```

- [ ] **Step 5: Run all tests**

```bash
cd backend
.venv\Scripts\python.exe -m pytest tests/ -v
```

Expected: all tests pass including the 3 new ones. The existing `test_critique_loop_escalates_after_5_iterations` and `test_critique_loop_exits_on_approval` will need their unpacking updated (see Task 3).

- [ ] **Step 6: Commit**

```bash
git add app/agents/agent_critique.py tests/test_critique_loop.py
git commit -m "feat: decompose non-atomic agents automatically in critique loop"
```

---

### Task 3: Fix existing tests — update unpack from single agent to list

**Files:**
- Modify: `backend/tests/test_critique_loop.py`

The two pre-existing tests unpack `result, final_agent, iterations` — they now receive `result, agents, iterations` where `agents` is a list.

- [ ] **Step 1: Update `test_critique_loop_escalates_after_5_iterations`**

```python
# Change this line:
result, final_agent, iterations = await run_critique_loop(...)
# To:
result, agents, iterations = await run_critique_loop(...)

# Change assertion:
assert iterations == 5
assert result.verdict in [
    CritiqueVerdict.NEEDS_REVISION,
    CritiqueVerdict.ESCALATE_AUTO_FIX,
    CritiqueVerdict.ESCALATE_RETHINK,
    CritiqueVerdict.ESCALATE_USER,
]
# Add:
assert len(agents) == 1
```

- [ ] **Step 2: Update `test_critique_loop_exits_on_approval`**

```python
# Change unpack:
result, agents, iterations = await run_critique_loop(...)

# Update assertion:
assert iterations == 1
assert result.verdict == CritiqueVerdict.APPROVED
assert agents[0].quality_score == 8.5   # was: final_agent.quality_score
```

- [ ] **Step 3: Run tests**

```bash
cd backend
.venv\Scripts\python.exe -m pytest tests/test_critique_loop.py -v
```

Expected: all 6 tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_critique_loop.py
git commit -m "test: update existing critique loop tests for list[AtomicAgent] return"
```

---

### Task 4: Update `ws_design.py` — handle list return + DAG surgery

**Files:**
- Modify: `backend/app/api/ws_design.py`

- [ ] **Step 1: Replace the `run_critique_loop` call and post-processing block**

Find the block from `final_critique, final_agent, iterations = await run_critique_loop(...)` to `await send("AGENT_STATE_CHANGE", ...)` (lines 88–105) and replace it with:

```python
            final_critique, result_agents, iterations = await run_critique_loop(
                agent, critique_agent, producer, "design_time", on_event=send
            )

            # DAG surgery: if decomposed, replace original node with sub-agents in series
            if len(result_agents) > 1:
                orig_node_id = f"node_{agent.agent_id}"
                # Find predecessors and successors of the original node
                predecessors = [
                    e.from_node for e in dag.edges if e.to_node == orig_node_id
                ]
                successors = [
                    e.to_node for e in dag.edges if e.from_node == orig_node_id
                ]
                # Remove original node and its edges
                dag.nodes.pop(orig_node_id, None)
                dag.edges = [
                    e for e in dag.edges
                    if e.from_node != orig_node_id and e.to_node != orig_node_id
                ]
                # Add sub-agent nodes in series
                prev_node_id = None
                for sub_agent in result_agents:
                    new_node_id = f"node_{sub_agent.agent_id}"
                    dag.add_node(DAGNode(
                        node_id=new_node_id,
                        agent_id=sub_agent.agent_id,
                        agent_name=sub_agent.agent_name,
                    ))
                    if prev_node_id:
                        dag.add_edge(DAGEdge(
                            edge_id=f"e_{prev_node_id}_{new_node_id}",
                            from_node=prev_node_id,
                            to_node=new_node_id,
                        ))
                    prev_node_id = new_node_id
                # Re-wire: predecessors → first sub-agent
                first_node_id = f"node_{result_agents[0].agent_id}"
                for pred in predecessors:
                    dag.add_edge(DAGEdge(
                        edge_id=f"e_{pred}_{first_node_id}",
                        from_node=pred,
                        to_node=first_node_id,
                    ))
                # Re-wire: last sub-agent → successors
                last_node_id = f"node_{result_agents[-1].agent_id}"
                for succ in successors:
                    dag.add_edge(DAGEdge(
                        edge_id=f"e_{last_node_id}_{succ}",
                        from_node=last_node_id,
                        to_node=succ,
                    ))
                await send("DAG_UPDATED", {
                    "dag": {
                        "nodes": [n.model_dump() for n in dag.nodes.values()],
                        "edges": [e.model_dump() for e in dag.edges],
                    },
                    "message": (
                        f"Agent '{agent.agent_name}' decomposed into "
                        f"{len(result_agents)} atomic sub-agents"
                    ),
                })

            for final_agent in result_agents:
                await send(
                    "CRITIQUE_COMPLETE",
                    {
                        "agent_id": final_agent.agent_id,
                        "iterations": iterations,
                        "verdict": final_critique.verdict,
                        "quality_score": final_critique.quality_score,
                        "critique": final_critique.model_dump(),
                    },
                )
                state = AgentState.APPROVED if final_critique.errors_remaining == 0 else AgentState.USER_ESCALATED
                if state == AgentState.APPROVED:
                    approved_count += 1
                await send("AGENT_STATE_CHANGE", {"agent_id": final_agent.agent_id, "state": state})
```

- [ ] **Step 2: Add `DAGNode` and `DAGEdge` to imports at the top of `ws_design.py`**

```python
from app.models.dag import DAGNode, DAGEdge
```

- [ ] **Step 3: Run the full test suite**

```bash
cd backend
.venv\Scripts\python.exe -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add app/api/ws_design.py
git commit -m "feat: DAG surgery — replace decomposed agent node with sub-agent series"
```

---

### Task 5: Update `ws_extend.py` and `websocket.py`

**Files:**
- Modify: `backend/app/api/ws_extend.py`
- Modify: `backend/app/api/websocket.py`

- [ ] **Step 1: Update `ws_extend.py`**

Find `final_critique, final_agent, iterations = await run_critique_loop(...)` and the block through `approved_new.append(...)` and replace with:

```python
            final_critique, result_agents, iterations = await run_critique_loop(
                agent, critique_agent, producer, "design_time", on_event=send
            )

            await send("CRITIQUE_COMPLETE", {
                "agent_id": agent.agent_id,
                "iterations": iterations,
                "verdict": final_critique.verdict,
                "quality_score": final_critique.quality_score,
                "critique": final_critique.model_dump(),
            })

            for final_agent in result_agents:
                state = AgentState.APPROVED if final_critique.errors_remaining == 0 else AgentState.USER_ESCALATED
                await send("AGENT_STATE_CHANGE", {"agent_id": final_agent.agent_id, "state": state})
                approved_new.append(final_agent.model_dump(exclude={"critique_history"}))
```

- [ ] **Step 2: Update `websocket.py`**

Find `final_critique, final_agent, iterations = await run_critique_loop(...)` and the block through `await send("AGENT_STATE_CHANGE", ...)` and replace with:

```python
            final_critique, result_agents, iterations = await run_critique_loop(
                agent, critique, producer, "design_time"
            )
            await send(
                "CRITIQUE_COMPLETE",
                {
                    "agent_id": agent.agent_id,
                    "iterations": iterations,
                    "verdict": final_critique.verdict,
                    "quality_score": final_critique.quality_score,
                    "critique": final_critique.model_dump(),
                },
            )
            for final_agent in result_agents:
                state = (
                    AgentState.APPROVED
                    if final_critique.errors_remaining == 0
                    else AgentState.USER_ESCALATED
                )
                if state == AgentState.APPROVED:
                    approved_count += 1
                await send("AGENT_STATE_CHANGE", {"agent_id": final_agent.agent_id, "state": state})
```

- [ ] **Step 3: Run full test suite**

```bash
cd backend
.venv\Scripts\python.exe -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add app/api/ws_extend.py app/api/websocket.py
git commit -m "feat: update ws_extend and websocket to handle decomposed agent lists"
```

---

### Task 6: Deploy

- [ ] **Step 1: Run full test suite one final time**

```bash
cd backend
.venv\Scripts\python.exe -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 2: Deploy**

```powershell
cd C:\Users\schinta\AgentMaster
.\deploy.ps1
```

Expected: `Service [agentmaster] revision [...] has been deployed and is serving 100 percent of traffic.`
