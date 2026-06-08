# New Pipeline Stale State Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix `DesignPage` showing the previous pipeline's agents and DAG when navigating to a new pipeline.

**Architecture:** Add a synchronous `useDesignStore.getState().reset()` call at the top of the `pipelineId` effect in `DesignPage.tsx`, before the async `getPipeline()` call. This clears stale store state immediately on navigation so the component renders a blank loading state instead of the previous pipeline's data.

**Tech Stack:** React 18, TypeScript, Zustand

---

### Task 1: Fix — Reset design store synchronously on pipeline navigation

**Files:**
- Modify: `frontend/src/pages/DesignPage.tsx:114-116`

The effect at line 114 currently calls `getPipeline(pipelineId)` without first clearing the store. The existing `reset()` inside `.then()` only fires after the HTTP response — leaving a window where stale data is rendered.

- [ ] **Step 1: Apply the fix**

In `frontend/src/pages/DesignPage.tsx`, find the `useEffect` at line 114 and add `useDesignStore.getState().reset();` as the first statement after the early-return guard:

**Before:**
```typescript
  useEffect(() => {
    if (!pipelineId) return;
    getPipeline(pipelineId)
```

**After:**
```typescript
  useEffect(() => {
    if (!pipelineId) return;
    useDesignStore.getState().reset();
    getPipeline(pipelineId)
```

- [ ] **Step 2: Verify the TypeScript compiles**

From the `frontend/` directory:
```bash
npx tsc --noEmit
```
Expected: No errors.

- [ ] **Step 3: Manual smoke test**

Start the dev server (`npm run dev` in `frontend/`) and the backend. Then:

1. Create or open **Pipeline A** — wait for its design to fully load (agents visible in the left column).
2. Navigate back to **My Pipelines** and open **Pipeline B** (or create a new pipeline).
3. Observe: the agent list and DAG should be **empty/blank immediately** on navigation — not showing Pipeline A's agents even for a moment.
4. Verify Pipeline B's saved blueprint (if any) hydrates correctly once the API responds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/DesignPage.tsx
git commit -m "fix: reset design store synchronously on pipeline navigation

Previously the design store was only reset inside the getPipeline().then()
callback, causing stale agents and DAG from the previous pipeline to flash
on screen during the async loading window.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 2: Push to remote

- [ ] **Step 1: Push**

```bash
git push
```

Expected: Branch pushed, no conflicts.
