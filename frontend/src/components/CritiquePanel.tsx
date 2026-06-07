import type { CritiqueResult } from "../types";

const VERDICT_COLORS: Record<string, string> = {
  APPROVED: "text-green-400",
  NEEDS_REVISION: "text-yellow-400",
  ESCALATE_AUTO_FIX: "text-orange-400",
  ESCALATE_RETHINK: "text-red-400",
  ESCALATE_USER: "text-red-600 font-bold",
};

const SEVERITY_BADGE: Record<string, string> = {
  critical: "bg-red-900 text-red-200 border border-red-700",
  major: "bg-orange-900 text-orange-200 border border-orange-700",
  minor: "bg-yellow-900 text-yellow-200 border border-yellow-700",
  informational: "bg-gray-800 text-gray-300 border border-gray-600",
};

export function CritiquePanel({ critique }: { critique: CritiqueResult }) {
  return (
    <div className="bg-gray-850 border border-gray-600 rounded p-3 text-xs font-mono mt-2 space-y-2">
      <div className="flex justify-between items-center">
        <span className="text-gray-400">
          Iteration {critique.iteration}/{critique.max_iterations}
        </span>
        <span className={`font-bold ${VERDICT_COLORS[critique.verdict] || "text-white"}`}>
          {critique.verdict}
        </span>
        <span className="text-gray-300">★ {critique.quality_score}/10</span>
      </div>

      {critique.issues.length > 0 && (
        <div className="space-y-1">
          {critique.issues.map((issue) => (
            <div
              key={issue.issue_id}
              className={`px-2 py-1 rounded text-xs ${SEVERITY_BADGE[issue.severity] || "bg-gray-700"}`}
            >
              <span className="font-bold uppercase">[{issue.severity}]</span>{" "}
              {issue.description}
              <div className="opacity-70 mt-0.5 text-xs">
                Fix: {issue.recommendation}
              </div>
            </div>
          ))}
        </div>
      )}

      {critique.approved_aspects.length > 0 && (
        <div className="text-green-400 text-xs">
          ✓ {critique.approved_aspects.join(" · ")}
        </div>
      )}
    </div>
  );
}
