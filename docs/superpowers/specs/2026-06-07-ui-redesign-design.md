# AgentMaster UI Redesign — Design Spec
**Date:** 2026-06-07  
**Status:** Approved  

---

## Overview

Redesign the AgentMaster frontend shell to use a **top tab bar navigation** (Option B) while preserving the existing 3-panel resizable workspaces for Design and Run. The goal is a more coherent, useful app that surfaces key information and actions without losing the power of the current workspace layout.

---

## 1. Navigation Shell

### Top Tab Bar (replaces isolated page headers)
A persistent top bar at `h-10` across all pages:

- **Left:** `⬡ AgentMaster` logo button → navigates to Pipelines tab
- **Centre tabs:** `Pipelines` | `✏ Design` | `▶ Run`
  - Active tab has a 2px bottom border in the tab's accent colour (orange for Design, green for Run, blue for Pipelines)
  - Design and Run tabs are only clickable when a pipeline is active (greyed otherwise)
- **Right:** Elapsed timer `⏱ Xs` during an active run; LLM token counter `🟡 Critique N/5 · X tokens` during active design

### Pipelines Tab (new home page)
Replaces `NewPipelinePage`. A full-width list view:

- **Header row:** "My Pipelines" title + `＋ New Pipeline` button (opens inline creation form or navigates to a creation form)
- **Pipeline rows:** Name (bold) · objective (truncated) · agent count · date · status badge
  - Status badges: `Designed` (blue), `Never Run` (grey), `Last Run: ✓` (green), `Last Run: ✗` (red)
- **Row actions (visible on hover):** `✏ Design` → navigates to Design tab for that pipeline | `▶ Run` → navigates to Run tab
- **Delete** via a `✕` hover button (existing behaviour kept)
- New pipeline creation: clicking `＋ New Pipeline` expands an inline objective textarea + submit button at the top of the list

---

## 2. Design Workspace

### Pipeline Context Bar (new, below tab bar)
A slim `py-1.5` bar showing:
- Pipeline name (bold) + objective text (truncated, muted)
- Right side: `＋ Extend` | `💾 Save` | `▶ Run` action buttons — always visible, replacing buttons currently buried inside panels

The existing Save modal and Extend modal are kept as-is; only their trigger buttons move here.

### Progress Strip
Kept unchanged. Slim pill row showing agent states (pending → active → done/error).

### Left Panel — Agent List
- Agent cards gain a **quality score badge** (`9/10`) top-right when `quality_score` is set
- The **active/currently-critiquing agent** card gets an animated glow border (amber/orange pulse)
- Pending agents remain at 45% opacity as today

### Centre Panel — Critique Detail
- **LLM stream preview box** added above the issues list: shows the streaming critique text as it arrives (the current header token counter moves here as inline context). Text appends live, cursor blinks at the end.
- Approved aspects section gets a collapsible `▸ N` toggle (currently always expanded)
- All other existing critique detail rendering is kept

### Right Panel — DAG + Log
No changes to layout or behaviour.

---

## 3. Run Workspace

### Pipeline Context Bar (new, below tab bar)
Same structure as Design:
- Pipeline name + objective
- Right side: `✏ Edit Design` button (navigates to Design tab) | `▶ Run Again` button (re-triggers run)

### Progress Strip
- Adds a **thin progress bar** (fills left-to-right as agents complete) overlaid at the bottom of the strip
- Adds an **agent counter** `1/4` at the right end of the strip

### Left Panel — Agent List
- Completed agent cards show their **primary output field** inline below the name:
  - Detect the first string/array field in `output` and render a one-line preview: `📄 log_files: ["/var/log/app.log"…]`
  - Running agent card gets a blue glow border (matching Design's amber glow pattern)

### Centre Panel — Result Detail
Rich structured output rendering (already deployed in revision 00012):
- File paths → amber `<code>` chips
- Arrays → bullet list with `▸` markers
- Numbers → purple monospace chips
- Long strings → formatted prose block
- Nested objects → collapsible labelled card

### Right Panel — DAG + Run Log
No changes.

---

## 4. Component Changes Summary

| File | Change |
|------|--------|
| `TopNav.tsx` | Replace select dropdown with tab bar (Pipelines / Design / Run); add token/timer slot |
| `NewPipelinePage.tsx` → `PipelinesPage.tsx` | Full list view with inline creation, status badges, hover actions |
| `DesignPage.tsx` | Add context bar with action buttons; move Save/Extend/Run triggers there |
| `RunPage.tsx` | Add context bar; add progress bar + counter to strip |
| `AgentListColumn.tsx` | Add quality score badge + active glow (Design); add output preview (Run) |
| `CritiqueDetailColumn.tsx` | Add LLM stream preview box; collapse approved aspects |
| `ProgressStrip.tsx` | Add progress bar fill + counter slot for Run mode |
| `App.tsx` / router | Pipelines tab route → `PipelinesPage`; Design/Run tabs context-aware |

---

## 5. Out of Scope

- No backend changes required
- No changes to WebSocket protocols or store shape
- No changes to the DAG visualisation or DagLogColumn
- No changes to the Extend / Save modal content

---

## 6. Success Criteria

- Navigating between Pipelines, Design, and Run requires only one click on the tab bar
- Pipeline name and objective are always visible in Design and Run workspaces
- Save / Extend / Run buttons are immediately discoverable without scrolling
- Agent quality score visible at a glance in the Design agent list
- LLM critique text streams visibly in the centre panel (not just a header token count)
- Run results show structured output with paths, lists, and values clearly distinguished
