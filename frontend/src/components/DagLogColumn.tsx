// frontend/src/components/DagLogColumn.tsx
import type { DAGData, InputField } from "../types";

interface LogEntry {
  type: string;
  text: string;
}

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

function DagNode({
  label,
  state,
  mode,
}: {
  label: string;
  state: string;
  mode: "design" | "run";
}) {
  const color =
    state === "APPROVED" || state === "COMPLETED" || state === "completed"
      ? "bg-green-700 border-green-500 text-green-100"
      : state === "failed"
      ? "bg-red-700 border-red-500 text-red-100"
      : state.startsWith("DESIGN_CRITIQUE") ||
        state === "REVISING_SPEC" ||
        state === "AUTO_FIX"
      ? "bg-amber-700 border-amber-500 text-amber-100"
      : state === "SPECIFYING" || state === "running" || state === "EXECUTING"
      ? mode === "run"
        ? "bg-purple-700 border-purple-500 text-purple-100"
        : "bg-cyan-700 border-cyan-500 text-cyan-100"
      : "bg-gray-800 border-gray-700 text-gray-500";

  return (
    <div
      className={`border rounded px-2 py-1 text-xs truncate max-w-[110px] ${color}`}
      title={label}
    >
      {label}
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

export function DagLogColumn({
  dag,
  agentStates,
  logs,
  inputFields,
  mode,
}: DagLogColumnProps) {
  return (
    <div className="flex flex-col h-full gap-3 font-mono">
      {/* DAG */}
      <div className="shrink-0">
        <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">
          Pipeline DAG
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-3 min-h-[80px]">
          {!dag ? (
            <div className="text-gray-700 text-xs text-center py-3">
              DAG appears after blueprint…
            </div>
          ) : (
            <div className="flex flex-wrap gap-1.5">
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

      {/* Required / provided inputs */}
      {inputFields.length > 0 && (
        <div className="shrink-0">
          <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">
            {mode === "design" ? "Required Inputs" : "Your Inputs"}
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-3">
            {inputFields.map((f) => (
              <div key={f.name} className="text-xs mb-2">
                <span
                  className={
                    mode === "design" ? "text-cyan-400" : "text-purple-400"
                  }
                >
                  {f.name}
                </span>
                <span className="text-gray-600"> ({f.type})</span>
                {f.required && <span className="text-red-500 ml-1">*</span>}
                <div className="text-gray-600 ml-2 mt-0.5 text-xs">
                  {f.description}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Log */}
      <div className="flex flex-col flex-1 min-h-0">
        <div className="text-xs text-gray-500 mb-2 shrink-0 uppercase tracking-wider">
          {mode === "design" ? "Design Log" : "Run Log"}
        </div>
        <div className="flex-1 bg-gray-900 border border-gray-800 rounded-lg overflow-y-auto p-3 text-xs min-h-0">
          {logs.length === 0 && (
            <div className="text-gray-700 text-center py-8">
              Waiting for events…
            </div>
          )}
          {[...logs].reverse().map((entry, i) => (
            <div
              key={i}
              className={`${
                LOG_COLOR[entry.type] || "text-gray-400"
              } mb-1 leading-relaxed`}
            >
              <span className="text-gray-700">[{entry.type}]</span>{" "}
              {entry.text}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
