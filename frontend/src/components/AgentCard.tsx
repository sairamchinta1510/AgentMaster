import { useState } from "react";
import type { AtomicAgent } from "../types";
import { CritiquePanel } from "./CritiquePanel";

const STATE_COLORS: Record<string, string> = {
  PENDING: "bg-gray-600",
  SPECIFYING: "bg-blue-600 animate-pulse",
  DESIGN_CRITIQUE_1: "bg-yellow-600 animate-pulse",
  DESIGN_CRITIQUE_2: "bg-yellow-600 animate-pulse",
  DESIGN_CRITIQUE_3: "bg-yellow-600 animate-pulse",
  DESIGN_CRITIQUE_4: "bg-orange-600 animate-pulse",
  DESIGN_CRITIQUE_5: "bg-red-600 animate-pulse",
  REVISING_SPEC: "bg-blue-500 animate-pulse",
  AUTO_FIX: "bg-orange-500 animate-pulse",
  RETHINK: "bg-purple-600 animate-pulse",
  APPROVED: "bg-green-600",
  COMPLETED: "bg-green-700",
  FAILED_ESCALATED: "bg-red-700",
  USER_ESCALATED: "bg-purple-600",
  SIMULATING: "bg-cyan-600 animate-pulse",
  VALIDATED: "bg-teal-600",
  EXECUTING: "bg-green-500 animate-pulse",
};

export function AgentCard({ agent }: { agent: AtomicAgent }) {
  const [showCritique, setShowCritique] = useState(false);
  const stateColor = STATE_COLORS[agent.state] || "bg-gray-700";
  const latestCritique = agent.critique_history[agent.critique_history.length - 1];

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 font-mono">
      <div className="flex justify-between items-start gap-2">
        <div className="flex-1 min-w-0">
          <div className="text-white font-bold text-sm truncate">{agent.agent_name}</div>
          <div className="text-gray-400 text-xs mt-0.5 line-clamp-2">{agent.description}</div>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <span className={`${stateColor} text-white text-xs px-2 py-0.5 rounded whitespace-nowrap`}>
            {agent.state}
          </span>
          {agent.quality_score !== null && agent.quality_score !== undefined && (
            <span className="text-green-400 text-xs">★ {agent.quality_score}/10</span>
          )}
        </div>
      </div>

      {agent.critique_iterations > 0 && (
        <div className="mt-2 text-xs text-gray-500">
          Critique: {agent.critique_iterations}/5 iterations
          {latestCritique && (
            <button
              className="ml-2 text-blue-400 underline text-xs"
              onClick={() => setShowCritique((v) => !v)}
            >
              {showCritique ? "hide" : "show"}
            </button>
          )}
        </div>
      )}

      {showCritique && latestCritique && <CritiquePanel critique={latestCritique} />}
    </div>
  );
}
