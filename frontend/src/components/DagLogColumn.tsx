// frontend/src/components/DagLogColumn.tsx
import type { DAGData, InputField } from "../types";

interface LogEntry { type: string; text: string; }

const LOG_COLOR: Record<string, string> = {
  DESIGN_STARTED:    "text-blue-400",
  PHASE_UPDATE:      "text-cyan-400",
  BLUEPRINT_READY:   "text-indigo-400",
  DAG_BUILT:         "text-indigo-300",
  AGENT_STARTED:     "text-yellow-300",
  AGENT_PRODUCED:    "text-green-300",
  CRITIQUE_COMPLETE: "text-purple-300",
  AGENT_STATE_CHANGE:"text-orange-300",
  DESIGN_COMPLETE:   "text-green-500",
  RUN_STARTED:       "text-blue-400",
  AGENT_RESULT:      "text-green-300",
  RUN_COMPLETE:      "text-green-500",
  ERROR:             "text-red-400",
};

function DagNodeBox({ label, state, mode }: { label: string; state: string; mode: "design" | "run" }) {
  const cls =
    state === "APPROVED" || state === "COMPLETED" || state === "completed"
      ? "bg-[#071c0f] border-green-600 text-green-300"
      : state === "failed"
      ? "bg-[#1a0707] border-red-600 text-red-300"
      : state.startsWith("DESIGN_CRITIQUE") || state === "REVISING_SPEC" || state === "AUTO_FIX"
      ? "bg-[#1a1200] border-amber-600 text-amber-300"
      : state === "SPECIFYING" || state === "running" || state === "EXECUTING"
      ? mode === "run"
        ? "bg-[#110a24] border-purple-500 text-purple-300"
        : "bg-[#071828] border-cyan-500 text-cyan-300"
      : "bg-gray-900 border-gray-700 text-gray-500";

  const dot =
    state === "APPROVED" || state === "completed" ? "✓" :
    state === "failed" ? "✗" :
    (state.startsWith("DESIGN_CRITIQUE") || state === "running") ? "●" : "";

  return (
    <div className={`border rounded-lg px-3 py-2 text-xs font-mono flex items-center gap-2 w-full ${cls}`}>
      {dot && <span className={dot === "●" ? "animate-pulse" : ""}>{dot}</span>}
      <span className="truncate">{label}</span>
    </div>
  );
}

interface DagLogColumnProps {
  dag: DAGData | null;
  agentStates: Record<string, string>;
  logs: LogEntry[];
  inputFields: InputField[];
  mode: "design" | "run";
}

export function DagLogColumn({ dag, agentStates, logs, inputFields, mode }: DagLogColumnProps) {
  return (
    <div className="flex flex-col h-full gap-3 font-mono">
      {/* DAG */}
      <div className="shrink-0">
        <div className="text-xs text-gray-600 mb-2 uppercase tracking-widest">DAG</div>
        <div className="space-y-0">
          {!dag ? (
            <div className="text-gray-800 text-xs text-center py-4 border border-dashed border-gray-800 rounded-lg">
              appears after blueprint…
            </div>
          ) : (
            dag.nodes.map((n, i) => (
              <div key={n.node_id}>
                <DagNodeBox
                  label={n.agent_name}
                  state={agentStates[n.agent_id] || "PENDING"}
                  mode={mode}
                />
                {i < dag.nodes.length - 1 && (
                  <div className="text-gray-700 text-xs text-center leading-none py-0.5">↓</div>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Required inputs */}
      {inputFields.length > 0 && (
        <div className="shrink-0">
          <div className="text-xs text-gray-600 mb-2 uppercase tracking-widest">
            {mode === "design" ? "Required Inputs" : "Your Inputs"}
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-3 space-y-2">
            {inputFields.map((f) => (
              <div key={f.name} className="text-xs">
                <span className={mode === "design" ? "text-cyan-400" : "text-purple-400"}>{f.name}</span>
                <span className="text-gray-700"> ({f.type})</span>
                {f.required && <span className="text-red-500 ml-1">*</span>}
                <div className="text-gray-600 mt-0.5">{f.description}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Log */}
      <div className="flex flex-col flex-1 min-h-0">
        <div className="text-xs text-gray-600 mb-2 shrink-0 uppercase tracking-widest">
          {mode === "design" ? "Design Log" : "Run Log"}
        </div>
        <div className="flex-1 bg-[#0a0a0a] border border-gray-800 rounded-lg overflow-y-auto p-3 text-xs min-h-0">
          {logs.length === 0 && (
            <div className="text-gray-800 text-center py-6">waiting…</div>
          )}
          {[...logs].reverse().map((entry, i) => (
            <div key={i} className={`${LOG_COLOR[entry.type] || "text-gray-500"} mb-1 leading-relaxed`}>
              <span className="text-gray-800">[{entry.type}]</span> {entry.text}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
