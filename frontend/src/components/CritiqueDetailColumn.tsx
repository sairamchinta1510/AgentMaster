// frontend/src/components/CritiqueDetailColumn.tsx
import { useState } from "react";
import { useDesignStore } from "../store/runStore";
import type { AtomicAgent, CritiqueResult, CritiqueIssue } from "../types";

const CIRCLED = ["①","②","③","④","⑤","⑥","⑦","⑧","⑨","⑩","⑪","⑫","⑬","⑭","⑮"];

const SEVERITY_TAG: Record<CritiqueIssue["severity"], { cls: string; label: string }> = {
  critical:      { cls: "bg-red-900/50 text-red-300 border-red-700",         label: "CRITICAL" },
  major:         { cls: "bg-orange-900/50 text-orange-300 border-orange-700", label: "MAJOR" },
  minor:         { cls: "bg-yellow-900/50 text-yellow-300 border-yellow-700", label: "MINOR" },
  informational: { cls: "bg-gray-800 text-gray-400 border-gray-700",          label: "INFO" },
};

function IssueCard({ issue }: { issue: CritiqueIssue }) {
  const tag = SEVERITY_TAG[issue.severity] ?? SEVERITY_TAG.informational;
  return (
    <div className="border border-gray-800 rounded-xl p-3 text-xs mb-2 bg-[#0d1117]">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="text-white font-semibold">{issue.category || "Issue"}</div>
        <span className={`border rounded px-2 py-0.5 text-xs shrink-0 font-bold ${tag.cls}`}>{tag.label}</span>
      </div>
      <div className="text-gray-400 mb-2">{issue.description}</div>
      {issue.recommendation && (
        <div className="text-gray-500 text-xs">→ {issue.recommendation}</div>
      )}
      {issue.auto_fixable && (
        <div className="mt-2 flex items-center gap-1.5 text-cyan-400">
          <span>⚡</span>
          <span className="text-xs">auto-fixing {issue.recommendation?.slice(0, 40) ?? ""}</span>
        </div>
      )}
    </div>
  );
}

function RoundTracker({ critiques, state }: { critiques: CritiqueResult[]; state: AtomicAgent["state"] }) {
  const activeIdx = state.startsWith("DESIGN_CRITIQUE") ? parseInt(state.slice(-1)) - 1 : null;

  const labels: Record<number, string> = {};
  critiques.forEach((c, i) => {
    if (!c) return;
    if (c.verdict === "APPROVED") labels[i] = "approved";
    else if (i === 0) labels[i] = "crit";
    else labels[i] = "revised";
  });
  if (activeIdx !== null) labels[activeIdx] = "▶ now";

  return (
    <div className="flex items-end gap-0 mb-5">
      {Array.from({ length: 5 }).map((_, i) => {
        const isDone = i < critiques.length;
        const isActive = i === activeIdx;
        const verdict = critiques[i]?.verdict;
        const circleColor =
          isActive    ? "border-amber-400 text-amber-300" :
          isDone && verdict === "APPROVED" ? "border-green-500 text-green-300 bg-green-900/20" :
          isDone      ? "border-amber-600 text-amber-400" :
                        "border-gray-700 text-gray-600";

        return (
          <div key={i} className="flex items-center">
            <div className="flex flex-col items-center">
              <div className={`h-8 w-8 rounded-full border-2 flex items-center justify-center text-sm font-bold ${circleColor} ${isActive ? "animate-pulse" : ""}`}>
                {i + 1}
              </div>
              <div className="text-xs text-gray-600 mt-1 w-10 text-center truncate">
                {labels[i] ?? "—"}
              </div>
            </div>
            {i < 4 && <div className={`h-px w-5 mb-4 ${isDone ? "bg-amber-700" : "bg-gray-800"}`} />}
          </div>
        );
      })}
    </div>
  );
}

interface CritiqueDetailColumnProps {
  agent: AtomicAgent | null;
  agentIndex?: number;
}

export function CritiqueDetailColumn({ agent, agentIndex }: CritiqueDetailColumnProps) {
  if (!agent) {
    return (
      <div className="flex h-full items-center justify-center text-gray-700 text-xs font-mono">
        ← Select an agent to see critique detail
      </div>
    );
  }

  const critiqueHistory = agent.critique_history ?? [];
  const latestCritique = critiqueHistory[critiqueHistory.length - 1];
  const isApproved = agent.state === "APPROVED" || agent.state === "COMPLETED";
  const isCritiquing = agent.state.startsWith("DESIGN_CRITIQUE");
  const currentRound = isCritiquing ? agent.state.slice(-1) : null;
  const llmStreamText = useDesignStore((s) => s.llmStreamText);
  const [aspectsOpen, setAspectsOpen] = useState(false);

  const circled = agentIndex != null ? (CIRCLED[agentIndex] ?? `${agentIndex + 1}`) : "";

  return (
    <div className="flex flex-col h-full font-mono">
      {/* Header */}
      <div className="shrink-0 mb-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              {circled && <span className="text-xl text-amber-400 font-bold">{circled}</span>}
              <span className="text-white font-bold text-base">{agent.agent_name}</span>
            </div>
            <div className="text-gray-500 text-xs mt-0.5">{agent.description}</div>
          </div>
          {isApproved ? (
            <span className="bg-green-900/50 text-green-300 border border-green-700 text-xs px-2 py-1 rounded-lg shrink-0 font-bold">
              ✓ APPROVED {agent.quality_score != null ? `★${agent.quality_score}` : ""}
            </span>
          ) : isCritiquing ? (
            <span className="bg-orange-900/50 text-orange-300 border border-orange-700 text-xs px-2 py-1 rounded-lg shrink-0 font-bold animate-pulse">
              NEEDS REVISION R{currentRound}
            </span>
          ) : null}
        </div>
      </div>

      {/* Round tracker */}
      <RoundTracker critiques={critiqueHistory} state={agent.state} />

      {isCritiquing && llmStreamText && (
        <div className="shrink-0 mb-4 bg-[#0a0c14] border border-amber-800/40 rounded-xl p-3">
          <div className="text-xs text-amber-600 mb-1.5 uppercase tracking-wider flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse inline-block" />
            LLM thinking…
          </div>
          <div className="text-gray-400 text-xs leading-relaxed font-mono whitespace-pre-wrap break-words max-h-24 overflow-hidden">
            {llmStreamText}
            <span className="inline-block h-3 w-1.5 bg-amber-400 animate-pulse ml-0.5 align-middle" />
          </div>
        </div>
      )}

      {/* Issues */}
      <div className="flex-1 overflow-y-auto">
        {!latestCritique && (
          <div className="text-gray-700 text-xs text-center py-10 border border-dashed border-gray-800 rounded-xl">
            Critique details appear as rounds complete…
          </div>
        )}
        {latestCritique && (
          <>
            <div className="text-xs text-gray-500 mb-3 flex items-center gap-2">
              <span className="uppercase tracking-wider">
                Round {latestCritique.iteration}/{latestCritique.max_iterations}
              </span>
              <span className="text-gray-700">·</span>
              <span className={latestCritique.verdict === "APPROVED" ? "text-green-400" : "text-amber-400"}>
                {latestCritique.verdict}
              </span>
              <span className="text-gray-700">·</span>
              <span className="text-yellow-400">★{latestCritique.quality_score}/10</span>
            </div>

            {(latestCritique.issues ?? []).length === 0 ? (
              <div className="text-green-500 text-xs text-center py-4 border border-green-900/40 rounded-xl">
                ✓ No issues in this round
              </div>
            ) : (
              (latestCritique.issues ?? []).map((issue) => (
                <IssueCard key={issue.issue_id} issue={issue} />
              ))
            )}

            {(latestCritique.approved_aspects ?? []).length > 0 && (
              <div className="mt-3">
                <button
                  className="flex items-center gap-2 text-xs text-gray-600 hover:text-gray-400 uppercase tracking-wider mb-1.5 w-full text-left"
                  onClick={() => setAspectsOpen((v) => !v)}
                >
                  <span className="text-green-600">✓</span>
                  Approved aspects ({(latestCritique.approved_aspects ?? []).length})
                  <span className="ml-auto">{aspectsOpen ? "▲" : "▼"}</span>
                </button>
                {aspectsOpen && (latestCritique.approved_aspects ?? []).map((a, i) => (
                  <div key={i} className="text-xs text-green-500/70 mb-1 pl-2">✓ {String(a)}</div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
