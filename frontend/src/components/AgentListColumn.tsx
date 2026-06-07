// frontend/src/components/AgentListColumn.tsx
import type { AtomicAgent, AgentResult } from "../types";

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

function designStateBadge(state: AtomicAgent["state"]): { label: string; cls: string } {
  if (state === "APPROVED") return { label: "✓ Approved", cls: "text-green-400" };
  if (state === "COMPLETED") return { label: "✓ Done", cls: "text-green-400" };
  if (state.startsWith("DESIGN_CRITIQUE")) {
    const n = state.slice(-1);
    return { label: `Critiquing r${n}/5`, cls: "text-amber-400 animate-pulse" };
  }
  if (state === "REVISING_SPEC" || state === "AUTO_FIX")
    return { label: "Fixing…", cls: "text-amber-300 animate-pulse" };
  if (state === "SPECIFYING") return { label: "Designing…", cls: "text-cyan-400 animate-pulse" };
  if (state === "FAILED_ESCALATED") return { label: "⚠ Escalated", cls: "text-red-400" };
  return { label: state.toLowerCase(), cls: "text-gray-500" };
}

function CritiqueDots({
  iterations,
  state,
}: {
  iterations: number;
  state: AtomicAgent["state"];
}) {
  const activeRound = state.startsWith("DESIGN_CRITIQUE") ? parseInt(state.slice(-1)) : null;

  return (
    <div className="flex items-center gap-1 mt-1.5">
      {Array.from({ length: 5 }).map((_, i) => {
        const round = i + 1;
        const isDone =
          round < iterations + 1 || state === "APPROVED" || state === "COMPLETED";
        const isActive = round === activeRound;
        return (
          <div
            key={i}
            className={`h-1.5 w-1.5 rounded-full ${
              isActive
                ? "bg-amber-400 animate-pulse"
                : isDone
                ? "bg-green-500"
                : "bg-gray-700"
            }`}
          />
        );
      })}
      <span className="text-xs text-gray-600 ml-1">{iterations}/5</span>
    </div>
  );
}

function RunStatusBadge({
  result,
  isRunning,
}: {
  result?: AgentResult;
  isRunning: boolean;
}) {
  if (isRunning)
    return <span className="text-purple-400 text-xs animate-pulse">● Running…</span>;
  if (!result) return <span className="text-gray-600 text-xs">Waiting</span>;
  if (result.status === "completed")
    return (
      <span className="text-green-400 text-xs">
        ✓ {result.duration_ms ? `${result.duration_ms}ms` : "Done"}
      </span>
    );
  if (result.status === "failed")
    return <span className="text-red-400 text-xs">✗ Failed</span>;
  return <span className="text-gray-400 text-xs">{result.status}</span>;
}

// ── Design time list ─────────────────────────────────────────────────────────

interface DesignAgentListProps {
  agents: AtomicAgent[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function DesignAgentList({
  agents,
  selectedId,
  onSelect,
}: DesignAgentListProps) {
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
              className={`w-full text-left border-l-4 rounded-lg p-3 transition-colors text-xs font-mono ${designBorderColor(a.state)} ${
                isSelected
                  ? "bg-gray-800 border border-gray-600"
                  : "bg-gray-900 border border-gray-800 hover:bg-gray-800"
              }`}
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

interface RunAgentSpec {
  agent_id: string;
  agent_name: string;
  description?: string;
}

interface RunAgentListProps {
  agents: RunAgentSpec[];
  results: Record<string, AgentResult>;
  runningId: string | null;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function RunAgentList({
  agents,
  results,
  runningId,
  selectedId,
  onSelect,
}: RunAgentListProps) {
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
            result?.status === "completed"
              ? "border-l-green-500"
              : result?.status === "failed"
              ? "border-l-red-500"
              : isRunning
              ? "border-l-purple-500"
              : "border-l-gray-700";
          return (
            <button
              key={a.agent_id}
              onClick={() => onSelect(a.agent_id)}
              className={`w-full text-left border-l-4 rounded-lg p-3 transition-colors text-xs font-mono ${borderCls} ${
                isSelected
                  ? "bg-gray-800 border border-gray-600"
                  : "bg-gray-900 border border-gray-800 hover:bg-gray-800"
              }`}
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
