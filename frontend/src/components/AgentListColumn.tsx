// frontend/src/components/AgentListColumn.tsx
import type { AtomicAgent, AgentResult } from "../types";

const CIRCLED = ["①","②","③","④","⑤","⑥","⑦","⑧","⑨","⑩","⑪","⑫","⑬","⑭","⑮","⑯","⑰","⑱","⑲","⑳"];

function cardColors(state: AtomicAgent["state"]): { border: string; bg: string; numColor: string } {
  if (state === "APPROVED" || state === "COMPLETED")
    return { border: "border-l-green-500", bg: "bg-[#071c0f]", numColor: "text-green-400" };
  if (state.startsWith("DESIGN_CRITIQUE") || state === "REVISING_SPEC" || state === "AUTO_FIX")
    return { border: "border-l-amber-500", bg: "bg-[#1a1200]", numColor: "text-amber-400" };
  if (state === "SPECIFYING")
    return { border: "border-l-cyan-500", bg: "bg-[#071828]", numColor: "text-cyan-400" };
  if (state === "FAILED_ESCALATED")
    return { border: "border-l-red-500", bg: "bg-[#1a0707]", numColor: "text-red-400" };
  return { border: "border-l-gray-700", bg: "bg-gray-900", numColor: "text-gray-600" };
}

function designStateBadge(state: AtomicAgent["state"]): { label: string; cls: string } {
  if (state === "APPROVED" || state === "COMPLETED") return { label: "✓ approved", cls: "text-green-400" };
  if (state.startsWith("DESIGN_CRITIQUE")) {
    const n = state.slice(-1);
    return { label: `critiquing r${n}/5`, cls: "text-amber-400 animate-pulse" };
  }
  if (state === "REVISING_SPEC" || state === "AUTO_FIX") return { label: "fixing…", cls: "text-amber-300 animate-pulse" };
  if (state === "SPECIFYING") return { label: "designing…", cls: "text-cyan-400 animate-pulse" };
  if (state === "FAILED_ESCALATED") return { label: "⚠ escalated", cls: "text-red-400" };
  return { label: state.toLowerCase(), cls: "text-gray-600" };
}

function CritiqueDots({ iterations, state }: { iterations: number; state: AtomicAgent["state"] }) {
  const safeIterations = iterations ?? 0;
  const activeRound = state.startsWith("DESIGN_CRITIQUE") ? parseInt(state.slice(-1)) : null;

  return (
    <div className="flex items-center gap-1 mt-1.5">
      {Array.from({ length: 5 }).map((_, i) => {
        const round = i + 1;
        const isDone = round <= safeIterations;
        const isActive = round === activeRound;
        return (
          <div
            key={i}
            className={`h-2 w-2 rounded-full border ${
              isActive ? "bg-amber-400 border-amber-300 animate-pulse" :
              isDone   ? "bg-amber-600 border-amber-500" :
                         "bg-gray-800 border-gray-700"
            }`}
          />
        );
      })}
    </div>
  );
}

interface DesignAgentListProps {
  agents: AtomicAgent[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function DesignAgentList({ agents, selectedId, onSelect }: DesignAgentListProps) {
  return (
    <div className="flex flex-col h-full">
      <div className="text-xs text-gray-500 mb-3 shrink-0 uppercase tracking-widest font-mono">
        Agents ({agents.length})
      </div>
      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        {agents.length === 0 && (
          <div className="text-gray-700 text-xs text-center py-10 border border-dashed border-gray-800 rounded-xl">
            Designing blueprint…
          </div>
        )}
        {agents.map((a, idx) => {
          const { border, bg, numColor } = cardColors(a.state);
          const { label, cls } = designStateBadge(a.state);
          const isSelected = a.agent_id === selectedId;
          return (
            <button
              key={a.agent_id}
              onClick={() => onSelect(a.agent_id)}
              className={`w-full text-left border-l-4 rounded-xl p-3 transition-all font-mono ${border} ${bg} ${
                isSelected ? "ring-1 ring-gray-500" : "hover:brightness-125"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className={`text-lg font-bold shrink-0 ${numColor}`}>{CIRCLED[idx] ?? idx + 1}</span>
                <span className="text-white font-semibold text-sm truncate">{a.agent_name}</span>
              </div>
              <CritiqueDots iterations={a.critique_iterations ?? 0} state={a.state} />
              <div className={`text-xs mt-1.5 flex items-center gap-2 ${cls}`}>
                <span>{label}</span>
                {a.quality_score != null && (
                  <span className="text-yellow-400 font-bold">★{a.quality_score}</span>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ── Run time ────────────────────────────────────────────────────────────────

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
      <div className="text-xs text-gray-500 mb-3 shrink-0 uppercase tracking-widest font-mono">
        Agents ({agents.length})
      </div>
      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        {agents.map((a, idx) => {
          const result = results[a.agent_id];
          const isRunning = a.agent_id === runningId;
          const isSelected = a.agent_id === selectedId;
          const { border, bg, numColor } =
            result?.status === "completed" ? { border: "border-l-green-500", bg: "bg-[#071c0f]", numColor: "text-green-400" } :
            result?.status === "failed"    ? { border: "border-l-red-500",   bg: "bg-[#1a0707]", numColor: "text-red-400" } :
            isRunning                      ? { border: "border-l-purple-500", bg: "bg-[#110a24]", numColor: "text-purple-400" } :
                                             { border: "border-l-gray-700",   bg: "bg-gray-900",  numColor: "text-gray-600" };

          return (
            <button
              key={a.agent_id}
              onClick={() => onSelect(a.agent_id)}
              className={`w-full text-left border-l-4 rounded-xl p-3 transition-all font-mono ${border} ${bg} ${
                isSelected ? "ring-1 ring-gray-500" : "hover:brightness-125"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className={`text-lg font-bold shrink-0 ${numColor}`}>{CIRCLED[idx] ?? idx + 1}</span>
                <span className="text-white font-semibold text-sm truncate">{a.agent_name}</span>
              </div>
              <div className="text-xs mt-1.5">
                {isRunning ? (
                  <span className="text-purple-400 animate-pulse">● running…</span>
                ) : result?.status === "completed" ? (
                  <span className="text-green-400">✓ completed {result.duration_ms ? `· ${result.duration_ms}ms` : ""}</span>
                ) : result?.status === "failed" ? (
                  <span className="text-red-400">✗ failed</span>
                ) : (
                  <span className="text-gray-600">waiting</span>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
