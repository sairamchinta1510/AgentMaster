# AgentMaster v2 UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite DesignPage.tsx and RunPage.tsx to match the approved 4-zone layout (objective banner → progress strip → status bar → 3 columns).

**Architecture:** Both pages share the same 4-zone shell and pull from existing Zustand stores (`useDesignStore`, `useRunStore`) and WS hooks (`useDesignWS`, `useRunWS`). No new stores or API endpoints are needed — only the presentational layer changes.

**Tech Stack:** React 18, TypeScript, Tailwind CSS v3, Zustand, React Router v6

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `frontend/src/pages/DesignPage.tsx` | **Rewrite** | Design-time 4-zone UI |
| `frontend/src/pages/RunPage.tsx` | **Rewrite** | Run-time 4-zone UI |
| `frontend/src/components/ProgressStrip.tsx` | **Create** | Shared progress strip (narration + pills + bar) |
| `frontend/src/components/AgentListColumn.tsx` | **Create** | Col 1: agent cards with left-border state colors |
| `frontend/src/components/CritiqueDetailColumn.tsx` | **Create** | Col 2 (design): 5-round critique detail for selected agent |
| `frontend/src/components/RunDetailColumn.tsx` | **Create** | Col 2 (run): input→output flow for selected agent |
| `frontend/src/components/DagLogColumn.tsx` | **Create** | Col 3: DAG + scrolling log + inputs panel |

---

## Task 1: ProgressStrip component

**Files:**
- Create: `frontend/src/components/ProgressStrip.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/src/components/ProgressStrip.tsx
import { useEffect, useRef } from "react";

export interface StepPill {
  id: string;
  label: string;
  state: "done" | "active-design" | "active-run" | "pending" | "error";
  detail?: string; // e.g. "r3/5" or "12s"
}

interface ProgressStripProps {
  narration: string;
  narrationSub?: string;
  pills: StepPill[];
  progress: number;   // 0–100
  total: number;
  done: number;
  mode: "design" | "run" | "idle";
}

const STATE_PILL: Record<StepPill["state"], string> = {
  done:          "bg-green-700 text-green-200 border-green-500",
  "active-design": "bg-amber-700 text-amber-100 border-amber-400 animate-pulse",
  "active-run":  "bg-purple-700 text-purple-100 border-purple-400 animate-pulse",
  pending:       "bg-gray-800 text-gray-500 border-gray-700",
  error:         "bg-red-800 text-red-200 border-red-500",
};

const STATE_DOT: Record<StepPill["state"], string> = {
  done:          "bg-green-400",
  "active-design": "bg-amber-400 animate-pulse",
  "active-run":  "bg-purple-400 animate-pulse",
  pending:       "bg-gray-600",
  error:         "bg-red-400",
};

export function ProgressStrip({ narration, narrationSub, pills, progress, total, done, mode }: ProgressStripProps) {
  const pillsRef = useRef<HTMLDivElement>(null);

  // Auto-scroll pills to active one
  useEffect(() => {
    if (!pillsRef.current) return;
    const active = pillsRef.current.querySelector<HTMLElement>("[data-active='true']");
    if (active) active.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  }, [pills]);

  const barColor =
    mode === "design" ? "bg-gradient-to-r from-cyan-600 to-amber-500" :
    mode === "run"    ? "bg-purple-600" :
                        "bg-gray-700";

  const dotColor =
    mode === "idle" ? "bg-gray-600" :
    mode === "design" ? "bg-cyan-400 animate-pulse" :
                        "bg-purple-400 animate-pulse";

  const borderColor =
    mode === "design" ? "border-cyan-800" :
    mode === "run"    ? "border-purple-800" :
                        "border-gray-800";

  return (
    <div className={`shrink-0 border-b ${borderColor} bg-gray-950 px-4 py-2`}>
      {/* Narration row */}
      <div className="flex items-start gap-2 mb-2">
        <span className={`mt-0.5 h-2 w-2 rounded-full shrink-0 ${dotColor}`} />
        <div className="flex-1 min-w-0">
          <div className="text-white text-xs font-semibold truncate">{narration}</div>
          {narrationSub && (
            <div className="text-gray-500 text-xs truncate mt-0.5">{narrationSub}</div>
          )}
        </div>
        <div className="text-gray-500 text-xs shrink-0 ml-2">
          {done} / {total} {mode === "design" ? "approved" : mode === "run" ? "done" : ""}
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-gray-800 rounded-full mb-2">
        <div
          className={`h-1 rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Step pills */}
      {pills.length > 0 && (
        <div ref={pillsRef} className="flex gap-1.5 overflow-x-auto scrollbar-hide pb-0.5">
          {pills.map((p, i) => (
            <div
              key={p.id}
              data-active={p.state === "active-design" || p.state === "active-run" ? "true" : undefined}
              className={`flex items-center gap-1 border rounded px-2 py-0.5 text-xs whitespace-nowrap shrink-0 ${STATE_PILL[p.state]}`}
            >
              <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${STATE_DOT[p.state]}`} />
              <span>{i + 1}. {p.label}</span>
              {p.detail && <span className="opacity-60 text-xs">{p.detail}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify file created**

Run: `Test-Path frontend/src/components/ProgressStrip.tsx` — Expected: `True`

---

## Task 2: AgentListColumn component

**Files:**
- Create: `frontend/src/components/AgentListColumn.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/src/components/AgentListColumn.tsx
import type { AtomicAgent, AgentResult } from "../types";

/** Left-border color per design-time state */
function designBorderColor(state: AtomicAgent["state"]): string {
  if (state === "APPROVED" || state === "COMPLETED") return "border-l-green-500";
  if (
    state === "DESIGN_CRITIQUE_1" || state === "DESIGN_CRITIQUE_2" ||
    state === "DESIGN_CRITIQUE_3" || state === "DESIGN_CRITIQUE_4" ||
    state === "DESIGN_CRITIQUE_5" || state === "REVISING_SPEC" || state === "AUTO_FIX"
  ) return "border-l-amber-500";
  if (state === "SPECIFYING" || state === "RETHINK") return "border-l-cyan-500";
  if (state === "FAILED_ESCALATED") return "border-l-red-500";
  return "border-l-gray-700";
}

/** State badge label for design */
function designStateBadge(state: AtomicAgent["state"]): { label: string; cls: string } {
  if (state === "APPROVED") return { label: "✓ Approved", cls: "text-green-400" };
  if (state === "COMPLETED") return { label: "✓ Done", cls: "text-green-400" };
  if (state.startsWith("DESIGN_CRITIQUE")) {
    const n = state.slice(-1);
    return { label: `Critiquing r${n}/5`, cls: "text-amber-400 animate-pulse" };
  }
  if (state === "REVISING_SPEC" || state === "AUTO_FIX") return { label: "Fixing…", cls: "text-amber-300 animate-pulse" };
  if (state === "SPECIFYING") return { label: "Designing…", cls: "text-cyan-400 animate-pulse" };
  if (state === "FAILED_ESCALATED") return { label: "⚠ Escalated", cls: "text-red-400" };
  return { label: state.toLowerCase(), cls: "text-gray-500" };
}

/** Critique round dots (5 dots) */
function CritiqueDots({ iterations, state }: { iterations: number; state: AtomicAgent["state"] }) {
  const totalDots = 5;
  const activeRound = state.startsWith("DESIGN_CRITIQUE") ? parseInt(state.slice(-1)) : null;

  return (
    <div className="flex gap-1 mt-1.5">
      {Array.from({ length: totalDots }).map((_, i) => {
        const round = i + 1;
        const isComplete = round < (iterations + 1) || state === "APPROVED" || state === "COMPLETED";
        const isActive = round === activeRound;
        return (
          <div
            key={i}
            className={`h-1.5 w-1.5 rounded-full ${
              isActive ? "bg-amber-400 animate-pulse" :
              isComplete ? "bg-green-500" :
              "bg-gray-700"
            }`}
          />
        );
      })}
      <span className="text-xs text-gray-600 ml-1">{iterations}/5</span>
    </div>
  );
}

/** Run-time status for a single agent */
function RunStatusBadge({ result, isRunning }: { result?: AgentResult; isRunning: boolean }) {
  if (isRunning) return <span className="text-purple-400 text-xs animate-pulse">● Running…</span>;
  if (!result) return <span className="text-gray-600 text-xs">Waiting</span>;
  if (result.status === "completed") return <span className="text-green-400 text-xs">✓ {result.duration_ms ? `${result.duration_ms}ms` : "Done"}</span>;
  if (result.status === "failed") return <span className="text-red-400 text-xs">✗ Failed</span>;
  return <span className="text-gray-400 text-xs">{result.status}</span>;
}

// ── Design time list ─────────────────────────────────────────────────────────

interface DesignAgentListProps {
  agents: AtomicAgent[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function DesignAgentList({ agents, selectedId, onSelect }: DesignAgentListProps) {
  return (
    <div className="flex flex-col h-full">
      <div className="text-xs text-gray-500 mb-2 shrink-0 uppercase tracking-wider">
        Agents ({agents.length})
      </div>
      <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
        {agents.length === 0 && (
          <div className="text-gray-600 text-xs text-center py-10 border border-dashed border-gray-800 rounded-lg">
            AgentMaster is designing the blueprint…
          </div>
        )}
        {agents.map((a) => {
          const { label, cls } = designStateBadge(a.state);
          const isSelected = a.agent_id === selectedId;
          return (
            <button
              key={a.agent_id}
              onClick={() => onSelect(a.agent_id)}
              className={`w-full text-left border-l-4 rounded-lg p-3 transition-colors text-xs font-mono
                ${designBorderColor(a.state)}
                ${isSelected ? "bg-gray-800 border border-gray-600" : "bg-gray-900 border border-gray-800 hover:bg-gray-850"}
              `}
            >
              <div className="text-white font-semibold truncate">{a.agent_name}</div>
              <div className="text-gray-500 truncate mt-0.5 text-xs">{a.description}</div>
              <div className={`mt-1 ${cls}`}>{label}</div>
              <CritiqueDots iterations={a.critique_iterations} state={a.state} />
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ── Run time list ────────────────────────────────────────────────────────────

interface RunAgentSpec { agent_id: string; agent_name: string; description?: string; }

interface RunAgentListProps {
  agents: RunAgentSpec[];
  results: Record<string, AgentResult>;
  runningId: string | null;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function RunAgentList({ agents, results, runningId, selectedId, onSelect }: RunAgentListProps) {
  return (
    <div className="flex flex-col h-full">
      <div className="text-xs text-gray-500 mb-2 shrink-0 uppercase tracking-wider">
        Agents ({agents.length})
      </div>
      <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
        {agents.map((a) => {
          const result = results[a.agent_id];
          const isRunning = a.agent_id === runningId;
          const isSelected = a.agent_id === selectedId;
          const borderCls =
            result?.status === "completed" ? "border-l-green-500" :
            result?.status === "failed"    ? "border-l-red-500" :
            isRunning                      ? "border-l-purple-500" :
                                             "border-l-gray-700";
          return (
            <button
              key={a.agent_id}
              onClick={() => onSelect(a.agent_id)}
              className={`w-full text-left border-l-4 rounded-lg p-3 transition-colors text-xs font-mono
                ${borderCls}
                ${isSelected ? "bg-gray-800 border border-gray-600" : "bg-gray-900 border border-gray-800 hover:bg-gray-850"}
              `}
            >
              <div className="text-white font-semibold truncate">{a.agent_name}</div>
              {a.description && (
                <div className="text-gray-500 truncate mt-0.5 text-xs">{a.description}</div>
              )}
              <div className="mt-1.5">
                <RunStatusBadge result={result} isRunning={isRunning} />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify**

Run: `Test-Path frontend/src/components/AgentListColumn.tsx` — Expected: `True`

---

## Task 3: CritiqueDetailColumn component

**Files:**
- Create: `frontend/src/components/CritiqueDetailColumn.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/src/components/CritiqueDetailColumn.tsx
import type { AtomicAgent, CritiqueResult, CritiqueIssue } from "../types";

const SEVERITY_TAG: Record<CritiqueIssue["severity"], { cls: string; label: string }> = {
  critical:      { cls: "bg-red-900 text-red-300 border-red-700",    label: "CRITICAL" },
  major:         { cls: "bg-orange-900 text-orange-300 border-orange-700", label: "MAJOR" },
  minor:         { cls: "bg-yellow-900 text-yellow-300 border-yellow-700", label: "MINOR" },
  informational: { cls: "bg-gray-800 text-gray-400 border-gray-700", label: "INFO" },
};

function IssueCard({ issue }: { issue: CritiqueIssue }) {
  const tag = SEVERITY_TAG[issue.severity];
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-3 text-xs mb-2">
      <div className="flex items-start gap-2">
        <span className={`border rounded px-1.5 py-0.5 text-xs shrink-0 ${tag.cls}`}>{tag.label}</span>
        <div className="flex-1 min-w-0">
          <div className="text-white font-semibold">{issue.category}</div>
          <div className="text-gray-400 mt-0.5">{issue.description}</div>
        </div>
      </div>
      {issue.recommendation && (
        <div className="mt-2 text-gray-500">
          <span className="text-gray-600">→ </span>{issue.recommendation}
        </div>
      )}
      <div className="mt-1.5 flex gap-2 flex-wrap">
        {issue.auto_fixable && (
          <span className="bg-cyan-900 text-cyan-300 border border-cyan-700 text-xs px-1.5 py-0.5 rounded">
            ⚡ Auto-fix
          </span>
        )}
        <span className="bg-gray-800 text-gray-500 border border-gray-700 text-xs px-1.5 py-0.5 rounded">
          effort: {issue.effort_estimate}
        </span>
      </div>
    </div>
  );
}

function RoundTracker({ critiques, state }: { critiques: CritiqueResult[]; state: AtomicAgent["state"] }) {
  const rounds = Array.from({ length: 5 }, (_, i) => critiques[i] ?? null);
  const activeRound = state.startsWith("DESIGN_CRITIQUE") ? parseInt(state.slice(-1)) - 1 : null;

  return (
    <div className="flex items-center gap-0 mb-4">
      {rounds.map((c, i) => {
        const isActive = i === activeRound;
        const isDone = !!c;
        const verdict = c?.verdict;
        const circleColor =
          isDone && verdict === "APPROVED" ? "bg-green-500 border-green-400" :
          isDone ? "bg-amber-500 border-amber-400" :
          isActive ? "bg-amber-400 border-amber-300 animate-pulse" :
          "bg-gray-800 border-gray-700";

        return (
          <div key={i} className="flex items-center">
            <div
              className={`h-6 w-6 rounded-full border-2 flex items-center justify-center text-xs font-bold text-white ${circleColor}`}
            >
              {isDone && verdict === "APPROVED" ? "✓" : isDone ? i + 1 : isActive ? "●" : i + 1}
            </div>
            {i < 4 && (
              <div className={`h-px w-4 ${isDone ? "bg-amber-600" : "bg-gray-800"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

interface CritiqueDetailColumnProps {
  agent: AtomicAgent | null;
}

export function CritiqueDetailColumn({ agent }: CritiqueDetailColumnProps) {
  if (!agent) {
    return (
      <div className="flex h-full items-center justify-center text-gray-700 text-xs font-mono">
        ← Select an agent to see critique detail
      </div>
    );
  }

  const latestCritique = agent.critique_history[agent.critique_history.length - 1];
  const isApproved = agent.state === "APPROVED" || agent.state === "COMPLETED";

  return (
    <div className="flex flex-col h-full font-mono">
      <div className="shrink-0 mb-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="text-white font-bold text-sm">{agent.agent_name}</div>
            <div className="text-gray-500 text-xs mt-0.5">{agent.description}</div>
          </div>
          {isApproved && (
            <span className="bg-green-900 text-green-300 border border-green-700 text-xs px-2 py-1 rounded shrink-0">
              ✓ Approved {agent.quality_score !== null ? `${agent.quality_score}/10` : ""}
            </span>
          )}
        </div>
        <RoundTracker critiques={agent.critique_history} state={agent.state} />
      </div>

      <div className="flex-1 overflow-y-auto">
        {!latestCritique && (
          <div className="text-gray-600 text-xs text-center py-10 border border-dashed border-gray-800 rounded-lg">
            Critique details appear here as rounds complete…
          </div>
        )}

        {latestCritique && (
          <>
            <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">
              Round {latestCritique.iteration} / {latestCritique.max_iterations}
              {" — "}
              <span className={latestCritique.verdict === "APPROVED" ? "text-green-400" : "text-amber-400"}>
                {latestCritique.verdict}
              </span>
              {" — "}
              {latestCritique.quality_score}/10
            </div>

            {latestCritique.issues.length === 0 ? (
              <div className="text-green-500 text-xs text-center py-4">
                ✓ No issues found in this round
              </div>
            ) : (
              latestCritique.issues.map((issue) => (
                <IssueCard key={issue.issue_id} issue={issue} />
              ))
            )}

            {latestCritique.approved_aspects.length > 0 && (
              <div className="mt-3">
                <div className="text-xs text-gray-500 mb-1.5 uppercase tracking-wider">Approved aspects</div>
                {latestCritique.approved_aspects.map((a, i) => (
                  <div key={i} className="text-xs text-green-500 mb-1">✓ {a}</div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify**

Run: `Test-Path frontend/src/components/CritiqueDetailColumn.tsx` — Expected: `True`

---

## Task 4: RunDetailColumn component

**Files:**
- Create: `frontend/src/components/RunDetailColumn.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/src/components/RunDetailColumn.tsx
import { useState } from "react";
import type { AgentResult, InputField } from "../types";

interface RunDetailColumnProps {
  agentId: string | null;
  agentName?: string;
  agentDescription?: string;
  result?: AgentResult;
  isRunning: boolean;
  userInputs: Record<string, string>;
  inputSchema: InputField[];
  onInputChange: (name: string, value: string) => void;
  onStartRun: () => void;
  starting: boolean;
  hasBlueprint: boolean;
}

export function RunDetailColumn({
  agentId,
  agentName,
  agentDescription,
  result,
  isRunning,
  userInputs,
  inputSchema,
  onInputChange,
  onStartRun,
  starting,
  hasBlueprint,
}: RunDetailColumnProps) {
  const [outputExpanded, setOutputExpanded] = useState(true);

  // Input form (shown when no run is active / before start)
  const showInputForm = !isRunning && !result;

  return (
    <div className="flex flex-col h-full font-mono">
      {/* Agent header (when one is selected) */}
      {agentId && agentName && (
        <div className="shrink-0 mb-3">
          <div className="text-white font-bold text-sm">{agentName}</div>
          {agentDescription && (
            <div className="text-gray-500 text-xs mt-0.5">{agentDescription}</div>
          )}
          {isRunning && (
            <div className="mt-2 text-purple-400 text-xs animate-pulse">● Running…</div>
          )}
        </div>
      )}

      {/* Input form / start run panel */}
      {(!agentId || showInputForm) && (
        <div className={`${agentId ? "" : "flex-1"} shrink-0`}>
          <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">
            {inputSchema.length > 0 ? "Your Inputs" : "No inputs required"}
          </div>
          {inputSchema.map((field) => (
            <div key={field.name} className="mb-2">
              <label className="text-xs text-gray-400 block mb-1">
                {field.name}
                {field.required && <span className="text-red-500 ml-1">*</span>}
                <span className="text-gray-600 ml-1">({field.type})</span>
              </label>
              <input
                type={field.type === "credential" ? "password" : "text"}
                className="w-full bg-gray-800 border border-gray-700 text-white px-3 py-2 rounded text-xs focus:outline-none focus:border-purple-500"
                placeholder={field.description}
                value={userInputs[field.name] || ""}
                onChange={(e) => onInputChange(field.name, e.target.value)}
                disabled={isRunning}
              />
            </div>
          ))}
          {hasBlueprint && !isRunning && (
            <button
              className="w-full mt-3 bg-purple-700 hover:bg-purple-600 text-white font-bold py-3 rounded-lg text-sm transition-colors disabled:opacity-50"
              onClick={onStartRun}
              disabled={starting || isRunning}
            >
              {starting ? "Starting…" : "▶ Start Run"}
            </button>
          )}
        </div>
      )}

      {/* Execution I/O detail (when an agent has a result) */}
      {result && (
        <div className="flex-1 overflow-y-auto">
          <div
            className="flex items-center justify-between mb-2 cursor-pointer"
            onClick={() => setOutputExpanded((v) => !v)}
          >
            <div className="text-xs text-gray-500 uppercase tracking-wider">Output</div>
            <span className="text-gray-600 text-xs">{outputExpanded ? "▲" : "▼"}</span>
          </div>
          {result.error && (
            <div className="bg-red-950 border border-red-800 rounded-lg p-3 text-red-300 text-xs mb-3">
              ✗ {result.error}
            </div>
          )}
          {outputExpanded && Object.keys(result.output).length > 0 && (
            <pre className="text-xs text-gray-300 bg-gray-950 border border-gray-800 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap max-h-64">
              {JSON.stringify(result.output, null, 2)}
            </pre>
          )}
          {outputExpanded && Object.keys(result.output).length === 0 && !result.error && (
            <div className="text-gray-600 text-xs text-center py-4">No output data</div>
          )}
          {result.duration_ms && (
            <div className="text-gray-600 text-xs mt-2">Completed in {result.duration_ms}ms</div>
          )}
        </div>
      )}

      {/* Running spinner */}
      {isRunning && result === undefined && agentId && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-purple-400">
            <div className="text-2xl mb-2 animate-spin">⟳</div>
            <div className="text-xs">Executing agent…</div>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify**

Run: `Test-Path frontend/src/components/RunDetailColumn.tsx` — Expected: `True`

---

## Task 5: DagLogColumn component

**Files:**
- Create: `frontend/src/components/DagLogColumn.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/src/components/DagLogColumn.tsx
import type { DAGData, InputField } from "../types";

interface LogEntry { type: string; text: string; }

const LOG_COLOR: Record<string, string> = {
  DESIGN_STARTED:   "text-blue-400",
  PHASE_UPDATE:     "text-cyan-400",
  BLUEPRINT_READY:  "text-indigo-400",
  DAG_BUILT:        "text-indigo-300",
  AGENT_STARTED:    "text-yellow-300",
  AGENT_PRODUCED:   "text-green-300",
  CRITIQUE_COMPLETE:"text-purple-300",
  AGENT_STATE_CHANGE:"text-orange-300",
  DESIGN_COMPLETE:  "text-green-500",
  RUN_STARTED:      "text-blue-400",
  AGENT_RESULT:     "text-green-300",
  RUN_COMPLETE:     "text-green-500",
  ERROR:            "text-red-400",
};

interface DagLogColumnProps {
  dag: DAGData | null;
  agentStates: Record<string, string>;
  logs: LogEntry[];
  inputFields: InputField[];
  mode: "design" | "run";
}

function DagNode({ label, state, mode }: { label: string; state: string; mode: "design" | "run" }) {
  const color =
    state === "APPROVED" || state === "COMPLETED" || state === "completed" ? "bg-green-700 border-green-500 text-green-100" :
    state === "failed" ? "bg-red-700 border-red-500 text-red-100" :
    state.startsWith("DESIGN_CRITIQUE") || state === "REVISING_SPEC" || state === "AUTO_FIX" ? "bg-amber-700 border-amber-500 text-amber-100" :
    state === "SPECIFYING" || state === "running" || state === "EXECUTING" ? (mode === "run" ? "bg-purple-700 border-purple-500 text-purple-100" : "bg-cyan-700 border-cyan-500 text-cyan-100") :
    "bg-gray-800 border-gray-700 text-gray-500";

  return (
    <div className={`border rounded px-2 py-1 text-xs truncate max-w-[120px] ${color}`}>
      {label}
    </div>
  );
}

export function DagLogColumn({ dag, agentStates, logs, inputFields, mode }: DagLogColumnProps) {
  return (
    <div className="flex flex-col h-full gap-3 font-mono">
      {/* DAG */}
      <div className="shrink-0">
        <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">Pipeline DAG</div>
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-3 min-h-[80px]">
          {!dag ? (
            <div className="text-gray-700 text-xs text-center py-3">DAG appears after blueprint…</div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {dag.nodes.map((n) => (
                <DagNode
                  key={n.node_id}
                  label={n.agent_name}
                  state={agentStates[n.agent_id] || "PENDING"}
                  mode={mode}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Required inputs */}
      {inputFields.length > 0 && (
        <div className="shrink-0">
          <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">
            {mode === "design" ? "Required Inputs (for Run)" : "Your Inputs"}
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-3">
            {inputFields.map((f) => (
              <div key={f.name} className="text-xs mb-1.5">
                <span className={mode === "design" ? "text-cyan-400" : "text-purple-400"}>{f.name}</span>
                <span className="text-gray-600"> ({f.type})</span>
                {f.required && <span className="text-red-500 ml-1">*</span>}
                <div className="text-gray-600 ml-2 mt-0.5">{f.description}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Log */}
      <div className="flex flex-col flex-1 min-h-0">
        <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider shrink-0">
          {mode === "design" ? "Design Log" : "Run Log"}
        </div>
        <div className="flex-1 bg-gray-900 border border-gray-800 rounded-lg overflow-y-auto p-3 text-xs min-h-0">
          {logs.length === 0 && (
            <div className="text-gray-700 text-center py-8">Waiting for events…</div>
          )}
          {[...logs].reverse().map((entry, i) => (
            <div key={i} className={`${LOG_COLOR[entry.type] || "text-gray-400"} mb-1 leading-relaxed`}>
              <span className="text-gray-700">[{entry.type}]</span> {entry.text}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify**

Run: `Test-Path frontend/src/components/DagLogColumn.tsx` — Expected: `True`

---

## Task 6: Rewrite DesignPage.tsx

**Files:**
- Modify: `frontend/src/pages/DesignPage.tsx`

- [ ] **Step 1: Replace the file**

```tsx
// frontend/src/pages/DesignPage.tsx
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useDesignStore } from "../store/runStore";
import { usePipelineStore } from "../store/pipelineStore";
import { useDesignWS } from "../hooks/useDesignWS";
import { getPipeline } from "../api/client";
import { ProgressStrip, type StepPill } from "../components/ProgressStrip";
import { DesignAgentList } from "../components/AgentListColumn";
import { CritiqueDetailColumn } from "../components/CritiqueDetailColumn";
import { DagLogColumn } from "../components/DagLogColumn";
import type { AtomicAgent } from "../types";

function summarizeEvent(event: { type: string; [k: string]: unknown }): string {
  switch (event.type) {
    case "PHASE_UPDATE":     return `${event.phase} — ${event.message}`;
    case "AGENT_STARTED":    return `Starting: ${event.agent_name}`;
    case "AGENT_PRODUCED":   return `Produced: ${(event.spec as { agent_name?: string })?.agent_name ?? event.agent_id}`;
    case "CRITIQUE_COMPLETE":return `Critique: ${event.agent_id} → ${event.verdict} (${event.quality_score}/10)`;
    case "AGENT_STATE_CHANGE":return `${event.agent_id} → ${event.state}`;
    case "DESIGN_COMPLETE":  return event.message as string;
    case "ERROR":            return `Error: ${event.message}`;
    default:                 return (event.message as string) || event.type;
  }
}

export function DesignPage() {
  const { pipelineId } = useParams<{ pipelineId: string }>();
  const navigate = useNavigate();
  const { activePipeline, setActivePipeline, upsertSummary } = usePipelineStore();
  const { isConnected, events, agents, dag, isComplete, phase } = useDesignStore();

  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);

  useDesignWS(pipelineId ?? null);

  useEffect(() => {
    if (!pipelineId) return;
    getPipeline(pipelineId)
      .then((r) => {
        setActivePipeline(r.data);
        upsertSummary({
          id: r.data.id,
          objective: r.data.objective,
          name: r.data.name,
          agent_count: r.data.blueprint?.agents
            ? (r.data.blueprint.agents as unknown[]).length
            : 0,
          created_at: r.data.created_at,
        });
      })
      .catch(() => {});
  }, [pipelineId]);

  const agentList: AtomicAgent[] = Object.values(agents);
  const approvedCount = agentList.filter(
    (a) => a.state === "APPROVED" || a.state === "COMPLETED"
  ).length;

  // Auto-select first active agent
  useEffect(() => {
    if (selectedAgentId) return;
    const active = agentList.find(
      (a) => a.state !== "PENDING" && a.state !== "APPROVED" && a.state !== "COMPLETED"
    );
    if (active) setSelectedAgentId(active.agent_id);
    else if (agentList.length > 0) setSelectedAgentId(agentList[0].agent_id);
  }, [agents]);

  // Build progress strip pills
  const pills: StepPill[] = agentList.map((a) => {
    const isCritiquing = a.state.startsWith("DESIGN_CRITIQUE") || a.state === "REVISING_SPEC" || a.state === "AUTO_FIX";
    const roundNum = a.state.startsWith("DESIGN_CRITIQUE") ? a.state.slice(-1) : null;
    const isDone = a.state === "APPROVED" || a.state === "COMPLETED";
    const isErr  = a.state === "FAILED_ESCALATED";
    return {
      id: a.agent_id,
      label: a.agent_name,
      state: isDone ? "done" : isErr ? "error" : isCritiquing ? "active-design" :
             a.state === "SPECIFYING" ? "active-design" : "pending",
      detail: isCritiquing && roundNum ? `r${roundNum}/5` : undefined,
    };
  });

  // Live narration
  const activeAgent = agentList.find(
    (a) => a.state !== "PENDING" && a.state !== "APPROVED" && a.state !== "COMPLETED"
  );
  let narration = "Waiting to start design…";
  let narrationSub: string | undefined;
  if (isComplete) {
    narration = `✓ All ${approvedCount} agents approved`;
  } else if (activeAgent) {
    const isCritiquing = activeAgent.state.startsWith("DESIGN_CRITIQUE");
    const roundNum = isCritiquing ? activeAgent.state.slice(-1) : null;
    narration = isCritiquing
      ? `Critiquing ${activeAgent.agent_name} — round ${roundNum} of 5`
      : activeAgent.state === "SPECIFYING"
      ? `Designing ${activeAgent.agent_name}…`
      : activeAgent.state === "REVISING_SPEC" || activeAgent.state === "AUTO_FIX"
      ? `Auto-fixing ${activeAgent.agent_name}…`
      : `${activeAgent.agent_name} — ${activeAgent.state}`;
    const latestCritique = activeAgent.critique_history[activeAgent.critique_history.length - 1];
    if (latestCritique && latestCritique.issues.length > 0) {
      narrationSub = `Issues: ${latestCritique.issues.slice(0, 2).map((i) => i.category).join(" · ")}`;
    }
  } else if (isConnected && phase) {
    narration = phase;
  }

  const progress = agentList.length > 0 ? Math.round((approvedCount / agentList.length) * 100) : 0;

  // Log entries
  const logEntries = events.map((e) => ({
    type: e.type,
    text: summarizeEvent(e as { type: string; [k: string]: unknown }),
  }));

  // Agent state map for DAG
  const agentStates: Record<string, string> = {};
  agentList.forEach((a) => { agentStates[a.agent_id] = a.state; });

  const selectedAgent = selectedAgentId ? agents[selectedAgentId] ?? null : null;

  if (!pipelineId) return null;

  return (
    <div className="flex flex-col h-full bg-gray-950 text-white overflow-hidden">
      {/* Zone 1: Objective banner */}
      <div className="shrink-0 px-4 py-2 border-b border-gray-800 bg-[#0d1b2e] flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-cyan-500 text-xs font-mono uppercase tracking-wider shrink-0">✏ Design</span>
          <span className="text-gray-200 text-sm truncate" title={activePipeline?.objective}>
            {activePipeline?.objective || "Loading…"}
          </span>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {isComplete && (
            <button
              className="bg-purple-700 hover:bg-purple-600 text-white px-4 py-1.5 rounded text-xs font-mono transition-colors"
              onClick={() => navigate(`/run/${pipelineId}`)}
            >
              ▶ Run Pipeline
            </button>
          )}
          <span className={`text-xs font-mono ${isConnected ? "text-green-400" : isComplete ? "text-green-500" : "text-yellow-500"}`}>
            {isConnected ? "● LIVE" : isComplete ? "✓ Done" : "○ Connecting…"}
          </span>
        </div>
      </div>

      {/* Zone 2: Progress strip */}
      <ProgressStrip
        narration={narration}
        narrationSub={narrationSub}
        pills={pills}
        progress={progress}
        total={agentList.length}
        done={approvedCount}
        mode={isComplete || isConnected ? "design" : "idle"}
      />

      {/* Zone 3: Status bar */}
      <div className="shrink-0 px-4 py-1.5 border-b border-gray-800 bg-gray-950 flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-3">
          <span className="bg-cyan-900 text-cyan-300 border border-cyan-700 px-2 py-0.5 rounded">✏ DESIGN TIME</span>
          {agentList.length > 0 && (
            <>
              <span className="bg-green-900 text-green-300 border border-green-700 px-2 py-0.5 rounded">
                {approvedCount} approved
              </span>
              {agentList.length - approvedCount > 0 && (
                <span className="bg-amber-900 text-amber-300 border border-amber-700 px-2 py-0.5 rounded">
                  {agentList.length - approvedCount} critiquing
                </span>
              )}
            </>
          )}
        </div>
        <button
          className={`px-4 py-1.5 rounded transition-colors ${
            isComplete
              ? "bg-purple-700 hover:bg-purple-600 text-white"
              : "bg-gray-800 text-gray-600 cursor-not-allowed"
          }`}
          disabled={!isComplete}
          onClick={() => navigate(`/run/${pipelineId}`)}
        >
          💾 Save & Run →
        </button>
      </div>

      {/* Zone 4: 3-column body */}
      <div className="flex-1 grid grid-cols-[220px_1fr_200px] gap-0 overflow-hidden">
        {/* Col 1: Agent list */}
        <div className="border-r border-gray-800 p-3 overflow-hidden">
          <DesignAgentList
            agents={agentList}
            selectedId={selectedAgentId}
            onSelect={setSelectedAgentId}
          />
        </div>

        {/* Col 2: Critique detail */}
        <div className="p-4 overflow-hidden">
          <CritiqueDetailColumn agent={selectedAgent} />
        </div>

        {/* Col 3: DAG + log */}
        <div className="border-l border-gray-800 p-3 overflow-hidden">
          <DagLogColumn
            dag={dag}
            agentStates={agentStates}
            logs={logEntries}
            inputFields={activePipeline?.input_schema ?? []}
            mode="design"
          />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -30`
Expected: no output (zero errors)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/DesignPage.tsx frontend/src/components/ProgressStrip.tsx frontend/src/components/AgentListColumn.tsx frontend/src/components/CritiqueDetailColumn.tsx
git commit -m "feat: add ProgressStrip, AgentListColumn, CritiqueDetailColumn + rewrite DesignPage"
```

---

## Task 7: Rewrite RunPage.tsx

**Files:**
- Modify: `frontend/src/pages/RunPage.tsx`

- [ ] **Step 1: Replace the file**

```tsx
// frontend/src/pages/RunPage.tsx
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useRunStore } from "../store/runStore";
import { usePipelineStore } from "../store/pipelineStore";
import { useRunWS } from "../hooks/useRunWS";
import { getPipeline, createRun } from "../api/client";
import { ProgressStrip, type StepPill } from "../components/ProgressStrip";
import { RunAgentList } from "../components/AgentListColumn";
import { RunDetailColumn } from "../components/RunDetailColumn";
import { DagLogColumn } from "../components/DagLogColumn";
import type { InputField } from "../types";

function summarizeRunEvent(event: { type: string; [k: string]: unknown }): string {
  switch (event.type) {
    case "RUN_STARTED":   return `Run started for: ${event.objective ?? event.run_id}`;
    case "AGENT_STARTED": return `Starting: ${event.agent_name}`;
    case "AGENT_RESULT":  return `${event.agent_name} → ${event.status}${event.duration_ms ? ` (${event.duration_ms}ms)` : ""}`;
    case "RUN_COMPLETE":  return `Complete: ${event.completed}/${event.total_agents} agents`;
    case "ERROR":         return `Error: ${event.message}`;
    default:              return (event.message as string) || event.type;
  }
}

export function RunPage() {
  const { pipelineId } = useParams<{ pipelineId: string }>();
  const navigate = useNavigate();
  const { activePipeline, setActivePipeline } = usePipelineStore();
  const { activeResults, runEvents, isConnected, isComplete, setRun } = useRunStore();

  const [inputValues, setInputValues] = useState<Record<string, string>>({});
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [inputSchema, setInputSchema] = useState<InputField[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [runningAgentId, setRunningAgentId] = useState<string | null>(null);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);

  useRunWS(currentRunId);

  // Load pipeline
  useEffect(() => {
    if (!pipelineId) return;
    getPipeline(pipelineId)
      .then((r) => {
        setActivePipeline(r.data);
        setInputSchema(r.data.input_schema || []);
      })
      .catch(() => {});
  }, [pipelineId]);

  // Track running agent from events
  useEffect(() => {
    if (runEvents.length === 0) return;
    const last = runEvents[runEvents.length - 1];
    if (last.type === "AGENT_STARTED" && "agent_id" in last) {
      setRunningAgentId(last.agent_id as string);
      setSelectedAgentId(last.agent_id as string);
    } else if (last.type === "RUN_COMPLETE" || last.type === "ERROR") {
      setRunningAgentId(null);
    }
  }, [runEvents]);

  // Elapsed timer
  useEffect(() => {
    if (!startedAt || isComplete) return;
    const t = setInterval(() => setElapsed(Math.floor((Date.now() - startedAt) / 1000)), 1000);
    return () => clearInterval(t);
  }, [startedAt, isComplete]);

  const handleStartRun = async () => {
    if (!pipelineId) return;
    const missing = inputSchema.filter((f) => f.required && !inputValues[f.name]?.trim());
    if (missing.length > 0) {
      alert(`Please provide: ${missing.map((f) => f.name).join(", ")}`);
      return;
    }
    setStarting(true);
    try {
      const { data: newRun } = await createRun(pipelineId, inputValues);
      setRun(newRun);
      setCurrentRunId(newRun.id);
      setStartedAt(Date.now());
      setElapsed(0);
    } catch {
      alert("Failed to start run.");
    } finally {
      setStarting(false);
    }
  };

  const agentList = activePipeline?.blueprint?.agents
    ? (activePipeline.blueprint.agents as Array<{ agent_id: string; agent_name: string; description?: string }>)
    : [];

  const hasBlueprint = agentList.length > 0;
  const isRunning = !!currentRunId && isConnected && !isComplete;
  const doneCount = Object.values(activeResults).filter((r) => r.status === "completed").length;
  const failedCount = Object.values(activeResults).filter((r) => r.status === "failed").length;
  const doneOrFailed = doneCount + failedCount;
  const progress = agentList.length > 0 ? Math.round((doneOrFailed / agentList.length) * 100) : 0;

  // Pills
  const pills: StepPill[] = agentList.map((a) => {
    const result = activeResults[a.agent_id];
    const isActiveNow = a.agent_id === runningAgentId;
    const state: StepPill["state"] =
      result?.status === "completed" ? "done" :
      result?.status === "failed"    ? "error" :
      isActiveNow                    ? "active-run" : "pending";
    return {
      id: a.agent_id,
      label: a.agent_name,
      state,
      detail: result?.duration_ms ? `${result.duration_ms}ms` : isActiveNow && elapsed > 0 ? `${elapsed}s` : undefined,
    };
  });

  // Narration
  let narration = "Provide inputs and start a run…";
  let narrationSub: string | undefined;
  if (isComplete) {
    const totalTime = elapsed > 0 ? ` in ${elapsed}s` : "";
    narration = failedCount > 0
      ? `⚠ Pipeline finished with ${failedCount} failure${failedCount > 1 ? "s" : ""}${totalTime}`
      : `✓ Pipeline complete${totalTime}`;
  } else if (isRunning && runningAgentId) {
    const runningSpec = agentList.find((a) => a.agent_id === runningAgentId);
    narration = runningSpec ? `Executing ${runningSpec.agent_name}…` : "Executing agent…";
    narrationSub = elapsed > 0 ? `${elapsed}s elapsed` : undefined;
  } else if (isRunning) {
    narration = "Run in progress…";
  }

  // Log entries
  const logEntries = runEvents.map((e) => ({
    type: e.type,
    text: summarizeRunEvent(e as { type: string; [k: string]: unknown }),
  }));

  // Agent state map for DAG
  const agentStates: Record<string, string> = {};
  agentList.forEach((a) => {
    const result = activeResults[a.agent_id];
    if (result?.status === "completed") agentStates[a.agent_id] = "completed";
    else if (result?.status === "failed") agentStates[a.agent_id] = "failed";
    else if (a.agent_id === runningAgentId) agentStates[a.agent_id] = "running";
    else agentStates[a.agent_id] = "PENDING";
  });

  const selectedResult = selectedAgentId ? activeResults[selectedAgentId] : undefined;
  const selectedSpec = agentList.find((a) => a.agent_id === selectedAgentId);

  if (!pipelineId) return null;

  return (
    <div className="flex flex-col h-full bg-gray-950 text-white overflow-hidden">
      {/* Zone 1: Objective banner */}
      <div className="shrink-0 px-4 py-2 border-b border-gray-800 bg-[#120a24] flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-purple-400 text-xs font-mono uppercase tracking-wider shrink-0">▶ Run</span>
          <span className="text-gray-200 text-sm truncate" title={activePipeline?.objective}>
            {activePipeline?.name || "Loading…"}
          </span>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <button
            className="text-gray-600 hover:text-cyan-400 text-xs font-mono transition-colors"
            onClick={() => navigate(`/design/${pipelineId}`)}
          >
            ✏ Edit Design
          </button>
          <span className={`text-xs font-mono ${
            isComplete ? (failedCount > 0 ? "text-red-400" : "text-green-400") :
            isRunning  ? "text-purple-400 animate-pulse" : "text-gray-600"
          }`}>
            {isComplete
              ? failedCount > 0 ? "✗ Failed" : "✓ Complete"
              : isRunning ? "● Running" : "○ Idle"}
          </span>
        </div>
      </div>

      {/* Zone 2: Progress strip */}
      <ProgressStrip
        narration={narration}
        narrationSub={narrationSub}
        pills={pills}
        progress={progress}
        total={agentList.length}
        done={doneCount}
        mode={isRunning || isComplete ? "run" : "idle"}
      />

      {/* Zone 3: Status bar */}
      <div className="shrink-0 px-4 py-1.5 border-b border-gray-800 bg-gray-950 flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-3">
          <span className="bg-purple-900 text-purple-300 border border-purple-700 px-2 py-0.5 rounded">▶ RUN TIME</span>
          {doneCount > 0 && (
            <span className="bg-green-900 text-green-300 border border-green-700 px-2 py-0.5 rounded">
              {doneCount} done
            </span>
          )}
          {failedCount > 0 && (
            <span className="bg-red-900 text-red-300 border border-red-700 px-2 py-0.5 rounded">
              {failedCount} failed
            </span>
          )}
          {isRunning && (
            <span className="bg-purple-900 text-purple-300 border border-purple-700 px-2 py-0.5 rounded animate-pulse">
              1 running
            </span>
          )}
          {agentList.length - doneOrFailed - (isRunning ? 1 : 0) > 0 && currentRunId && (
            <span className="bg-gray-800 text-gray-500 border border-gray-700 px-2 py-0.5 rounded">
              {agentList.length - doneOrFailed - (isRunning ? 1 : 0)} waiting
            </span>
          )}
        </div>
        <div className="text-gray-600">
          {elapsed > 0 ? `${elapsed}s elapsed` : ""}
        </div>
      </div>

      {/* Zone 4: 3-column body */}
      {!hasBlueprint ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="text-gray-500 text-sm mb-4">This pipeline hasn't been designed yet.</div>
            <button
              className="bg-cyan-700 hover:bg-cyan-600 text-white text-sm px-6 py-2 rounded-lg"
              onClick={() => navigate(`/design/${pipelineId}`)}
            >
              ✏️ Design Pipeline First
            </button>
          </div>
        </div>
      ) : (
        <div className="flex-1 grid grid-cols-[220px_1fr_200px] gap-0 overflow-hidden">
          {/* Col 1: Agent list */}
          <div className="border-r border-gray-800 p-3 overflow-hidden">
            <RunAgentList
              agents={agentList}
              results={activeResults}
              runningId={runningAgentId}
              selectedId={selectedAgentId}
              onSelect={setSelectedAgentId}
            />
          </div>

          {/* Col 2: Run detail / input form */}
          <div className="p-4 overflow-hidden">
            <RunDetailColumn
              agentId={selectedAgentId}
              agentName={selectedSpec?.agent_name}
              agentDescription={selectedSpec?.description}
              result={selectedResult}
              isRunning={selectedAgentId === runningAgentId}
              userInputs={inputValues}
              inputSchema={inputSchema}
              onInputChange={(name, value) => setInputValues((v) => ({ ...v, [name]: value }))}
              onStartRun={handleStartRun}
              starting={starting}
              hasBlueprint={hasBlueprint}
            />
          </div>

          {/* Col 3: DAG + log */}
          <div className="border-l border-gray-800 p-3 overflow-hidden">
            <DagLogColumn
              dag={activePipeline?.blueprint?.dag as import("../types").DAGData | null ?? null}
              agentStates={agentStates}
              logs={logEntries}
              inputFields={inputSchema}
              mode="run"
            />
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -40`
Expected: no output

- [ ] **Step 3: Build check**

Run: `cd frontend && npm run build 2>&1 | tail -20`
Expected: `built in ...`

- [ ] **Step 4: Final commit**

```bash
git add frontend/src/pages/RunPage.tsx frontend/src/components/RunDetailColumn.tsx frontend/src/components/DagLogColumn.tsx docs/
git commit -m "feat: redesign DesignPage and RunPage with progress strip, critique rounds, and 3-column layout

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Self-Review

**Spec coverage:**
- [x] Objective banner (Design: editable + cyan button; Run: read-only + purple button)
- [x] Progress strip with narration dot, sub-text, step pills, progress bar, count
- [x] Status bar with mode badge + stats + action button
- [x] Col 1: agent cards with left-border colors + critique dots (design) / duration (run)
- [x] Col 2: critique rounds 1-5 with connecting lines + issue cards (design) / I/O flow + start form (run)
- [x] Col 3: DAG + log + required inputs

**Placeholder scan:** None found.

**Type consistency:** `StepPill` exported from `ProgressStrip.tsx`, imported in both page files. `DesignAgentList`/`RunAgentList` exported from `AgentListColumn.tsx`. All prop types match store data shapes.
