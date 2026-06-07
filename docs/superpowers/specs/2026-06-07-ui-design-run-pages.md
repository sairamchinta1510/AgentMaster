# AgentMaster v2 UI — Design Time & Run Time Pages

**Date:** 2026-06-07  
**Status:** Approved

---

## Overview

Redesign the DesignPage and RunPage with a consistent 4-zone layout that keeps the user informed at all times — even while things are happening in the background.

## Layout (both pages share the same shell)

```
┌─────────────────────────────────────────────────────────┐
│  OBJECTIVE BANNER  │ editable input + action button      │
├─────────────────────────────────────────────────────────┤
│  PROGRESS STRIP    │ narration • step pills • bar        │  ← always visible
├─────────────────────────────────────────────────────────┤
│  STATUS BAR        │ mode badge • stats • save/done btn  │
├──────────────┬──────────────────────────┬───────────────┤
│  Agent List  │  Detail Panel            │  DAG + Log    │
│  (col 1)     │  (col 2, flexible)       │  (col 3)      │
└──────────────┴──────────────────────────┴───────────────┘
```

---

## Zone 1 — Objective Banner

**Design Time:**
- Text input showing pipeline objective (editable before design starts)
- `✏️ Design Pipeline` button (cyan) — triggers WS connection
- Locked/read-only once design WS is active

**Run Time:**
- Same input, read-only (shows objective from loaded pipeline)
- `▶ Run Pipeline` button (purple) — creates run record + triggers WS connection

---

## Zone 2 — Progress Strip (THE KEY ZONE)

Always visible. Contains:

1. **Live narration line** — animated dot + bold current action + sub-line detail
   - Design: *"Critiquing Vuln Scanner — round 3 of 5"* / sub: *"Auto-fixing: input_schema missing url · timeout too low"*
   - Run: *"Executing Vuln Scanner — scanning 247 files…"* / sub: *"12s elapsed · est. 30s remaining"*

2. **Step pills row** — one pill per agent, scrollable horizontally
   - `pill-done` (green): `① Repo Fetcher ✓`
   - `pill-active-design` (amber pulse): `③ Vuln Scanner ● r3/5`
   - `pill-active-run` (purple pulse): `③ Vuln Scanner ● 12s…`
   - `pill-pending` (dim): `④ Report Writer`

3. **Progress bar** — fills as agents complete (cyan for design, purple for run)

4. **Completion count** — right-aligned: `2 / 4 approved` or `2 / 4 done`

**Idle state (no active session):** Strip shows `Waiting to start…` with a dim bar at 0%.

---

## Zone 3 — Status Bar

Thin bar. Left: mode badge + short status text. Right: stat pills + primary action button.

- Design: `✏ DESIGN` badge · `2 approved` · `1 critiquing` · `💾 Save Execution Plan` (purple, disabled until all approved)
- Run: `▶ RUN` badge · `2 done` · `1 running` · `1 waiting`

---

## Zone 4 — 3-Column Body

### Column 1: Agent List (220px fixed)
- Agent card per agent, in design order
- Left-border color: green = approved/completed, amber pulse = critiquing, purple pulse = running, dim = waiting
- Card shows: agent name, short description, status tag, critique dots (design) or duration (run)

### Column 2: Detail Panel (flexible)
**Design Time — Critique Detail:**
- Agent name + description + verdict badge
- 5-step round tracker with connecting lines (fail/warn/active/empty circles)
- Issue cards with severity tags (MAJOR/MINOR/OK) + auto-fix pills
- Scrollable issue list

**Run Time — Execution Detail:**
- Agent name + description + running badge
- Progress bar + percentage
- Input → Output two-column layout
  - Inputs: user inputs + outputs from previous agents
  - Outputs: fills in live as they arrive, dashed border + pulsing while pending

### Column 3: DAG + Log (200px fixed)
- Mini DAG with color-coded nodes (green=done, amber=active-design, purple=active-run, dim=pending)
- Scrolling log (most recent at top)
- Required inputs panel (design) or provided inputs panel (run)

---

## Color Theming

| Element | Design Time | Run Time |
|---------|------------|---------|
| Accent | Cyan `#0284c7` | Purple `#7c3aed` |
| Banner bg | `#0d1b2e` | `#120a24` |
| Strip border | `#0284c7` | `#7c3aed` |
| Active agent | Amber `#f59e0b` | Purple `#a855f7` |
| Progress bar | Cyan→Amber gradient | Purple gradient |

---

## Behaviour

- Progress strip updates on every WS event
- Step pills appear as agents are produced (design) or started (run)
- Design complete → `💾 Save Execution Plan` button enables, strip shows `✓ All 4 agents approved`
- Run complete → strip shows `✓ Pipeline complete in 42s` (green)
- Error state → strip shows red narration dot + error message
