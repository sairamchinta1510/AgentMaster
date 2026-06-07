// frontend/src/components/CritiqueDetailColumn.tsx
import type { AtomicAgent, CritiqueResult, CritiqueIssue } from "../types";

const SEVERITY_TAG: Record<
  CritiqueIssue["severity"],
  { cls: string; label: string }
> = {
  critical:      { cls: "bg-red-900 text-red-300 border-red-700",         label: "CRITICAL" },
  major:         { cls: "bg-orange-900 text-orange-300 border-orange-700", label: "MAJOR" },
  minor:         { cls: "bg-yellow-900 text-yellow-300 border-yellow-700", label: "MINOR" },
  informational: { cls: "bg-gray-800 text-gray-400 border-gray-700",       label: "INFO" },
};

function IssueCard({ issue }: { issue: CritiqueIssue }) {
  const tag = SEVERITY_TAG[issue.severity];
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-3 text-xs mb-2">
      <div className="flex items-start gap-2">
        <span
          className={`border rounded px-1.5 py-0.5 text-xs shrink-0 ${tag.cls}`}
        >
          {tag.label}
        </span>
        <div className="flex-1 min-w-0">
          <div className="text-white font-semibold">{issue.category}</div>
          <div className="text-gray-400 mt-0.5">{issue.description}</div>
        </div>
      </div>
      {issue.recommendation && (
        <div className="mt-2 text-gray-500">
          <span className="text-gray-600">→ </span>
          {issue.recommendation}
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

function RoundTracker({
  critiques,
  state,
}: {
  critiques: CritiqueResult[];
  state: AtomicAgent["state"];
}) {
  const rounds = Array.from({ length: 5 }, (_, i) => critiques[i] ?? null);
  const activeRound = state.startsWith("DESIGN_CRITIQUE")
    ? parseInt(state.slice(-1)) - 1
    : null;

  return (
    <div className="flex items-center gap-0 mb-4">
      {rounds.map((c, i) => {
        const isActive = i === activeRound;
        const isDone = !!c;
        const verdict = c?.verdict;
        const circleColor =
          isDone && verdict === "APPROVED"
            ? "bg-green-500 border-green-400"
            : isDone
            ? "bg-amber-500 border-amber-400"
            : isActive
            ? "bg-amber-400 border-amber-300 animate-pulse"
            : "bg-gray-800 border-gray-700";

        return (
          <div key={i} className="flex items-center">
            <div
              className={`h-6 w-6 rounded-full border-2 flex items-center justify-center text-xs font-bold text-white ${circleColor}`}
            >
              {isDone && verdict === "APPROVED" ? "✓" : i + 1}
            </div>
            {i < 4 && (
              <div
                className={`h-px w-4 ${isDone ? "bg-amber-600" : "bg-gray-800"}`}
              />
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

  const latestCritique =
    agent.critique_history[agent.critique_history.length - 1];
  const isApproved =
    agent.state === "APPROVED" || agent.state === "COMPLETED";

  return (
    <div className="flex flex-col h-full font-mono">
      {/* Header */}
      <div className="shrink-0 mb-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="text-white font-bold text-sm">{agent.agent_name}</div>
            <div className="text-gray-500 text-xs mt-0.5">{agent.description}</div>
          </div>
          {isApproved && (
            <span className="bg-green-900 text-green-300 border border-green-700 text-xs px-2 py-1 rounded shrink-0">
              ✓ Approved{" "}
              {agent.quality_score !== null ? `${agent.quality_score}/10` : ""}
            </span>
          )}
        </div>
        <div className="mt-3">
          <RoundTracker critiques={agent.critique_history} state={agent.state} />
        </div>
      </div>

      {/* Critique content */}
      <div className="flex-1 overflow-y-auto">
        {!latestCritique && (
          <div className="text-gray-600 text-xs text-center py-10 border border-dashed border-gray-800 rounded-lg">
            Critique details appear here as rounds complete…
          </div>
        )}

        {latestCritique && (
          <>
            <div className="text-xs text-gray-500 mb-3 uppercase tracking-wider">
              Round {latestCritique.iteration} / {latestCritique.max_iterations}
              {" — "}
              <span
                className={
                  latestCritique.verdict === "APPROVED"
                    ? "text-green-400"
                    : "text-amber-400"
                }
              >
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
                <div className="text-xs text-gray-500 mb-1.5 uppercase tracking-wider">
                  Approved aspects
                </div>
                {latestCritique.approved_aspects.map((a, i) => (
                  <div key={i} className="text-xs text-green-500 mb-1">
                    ✓ {a}
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
