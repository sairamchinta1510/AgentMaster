# New Pipeline Stale State Fix — Design Spec
**Date:** 2026-06-07
**Scope:** Frontend bug fix — DesignPage stale store on pipeline navigation

---

## Problem

When a user navigates from one pipeline's design page to another (or creates a new pipeline), the DesignPage briefly displays the **previous pipeline's agents and DAG**. This happens because:

1. `DesignPage.tsx` has a `useEffect` that fetches the new pipeline via `getPipeline(pipelineId)` (async).
2. `useDesignStore.reset()` is only called inside the `.then()` callback — after the HTTP response arrives.
3. During the async window, React renders the component with stale store state (previous pipeline's data).

---

## Fix

**File:** `frontend/src/pages/DesignPage.tsx`

**Change:** Add `useDesignStore.getState().reset()` as the first synchronous statement inside the `useEffect` that depends on `[pipelineId, ...]`, before the `getPipeline()` call.

This immediately clears agents, DAG, events, and phase when `pipelineId` changes, so the component renders a clean loading state instead of stale data.

---

## Scope

- One-line change in `DesignPage.tsx`
- No backend changes
- No new dependencies
- Existing reset logic inside `.then()` remains as a safety net for the async hydration path

---

## Testing

- Navigate from Pipeline A's design page to Pipeline B — should show blank/loading state immediately, not Pipeline A's agents
- Create a new pipeline and navigate to its design page — should show empty state, not previous pipeline
- Refresh on an existing pipeline with a saved blueprint — should hydrate correctly from the API response
