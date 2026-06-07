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
    case "PHASE_UPDATE":      return `${event.phase} — ${event.message}`;
    case "AGENT_STARTED":     return `Starting: ${event.agent_name}`;
    case "AGENT_PRODUCED":    return `Produced: ${(event.spec as { agent_name?: string })?.agent_name ?? event.agent_id}`;
    case "CRITIQUE_COMPLETE": return `Critique: ${event.agent_id} → ${event.verdict} (${event.quality_score}/10)`;
    case "AGENT_STATE_CHANGE":return `${event.agent_id} → ${event.state}`;
    case "DESIGN_COMPLETE":   return event.message as string;
    case "ERROR":             return `Error: ${event.message}`;
    default:                  return (event.message as string) || event.type;
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

  // Auto-select first active or first agent
  useEffect(() => {
    if (selectedAgentId) return;
    const active = agentList.find(
      (a) => a.state !== "PENDING" && a.state !== "APPROVED" && a.state !== "COMPLETED"
    );
    const target = active ?? agentList[0];
    if (target) setSelectedAgentId(target.agent_id);
  }, [agents]);

  // Build progress strip pills
  const pills: StepPill[] = agentList.map((a) => {
    const isCritiquing =
      a.state.startsWith("DESIGN_CRITIQUE") ||
      a.state === "REVISING_SPEC" ||
      a.state === "AUTO_FIX";
    const roundNum = a.state.startsWith("DESIGN_CRITIQUE") ? a.state.slice(-1) : null;
    const isDone = a.state === "APPROVED" || a.state === "COMPLETED";
    const isErr  = a.state === "FAILED_ESCALATED";
    return {
      id: a.agent_id,
      label: a.agent_name,
      state: isDone ? "done" : isErr ? "error" :
             isCritiquing || a.state === "SPECIFYING" ? "active-design" : "pending",
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
    const latestCritique =
      activeAgent.critique_history[activeAgent.critique_history.length - 1];
    if (latestCritique && latestCritique.issues.length > 0) {
      narrationSub = `Issues: ${latestCritique.issues
        .slice(0, 2)
        .map((i) => i.category)
        .join(" · ")}`;
    }
  } else if (isConnected && phase) {
    narration = phase;
  }

  const progress =
    agentList.length > 0 ? Math.round((approvedCount / agentList.length) * 100) : 0;

  const logEntries = events.map((e) => ({
    type: e.type,
    text: summarizeEvent(e as { type: string; [k: string]: unknown }),
  }));

  const agentStates: Record<string, string> = {};
  agentList.forEach((a) => { agentStates[a.agent_id] = a.state; });

  const selectedAgent = selectedAgentId ? (agents[selectedAgentId] ?? null) : null;

  if (!pipelineId) return null;

  return (
    <div className="flex flex-col h-full bg-gray-950 text-white overflow-hidden">
      {/* Zone 1: Objective banner */}
      <div className="shrink-0 px-4 py-2 border-b border-gray-800 bg-[#0d1b2e] flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-cyan-500 text-xs font-mono uppercase tracking-wider shrink-0">
            ✏ Design
          </span>
          <span
            className="text-gray-200 text-sm truncate"
            title={activePipeline?.objective}
          >
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
          <span
            className={`text-xs font-mono ${
              isConnected
                ? "text-green-400"
                : isComplete
                ? "text-green-500"
                : "text-yellow-500"
            }`}
          >
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
        <div className="flex items-center gap-2 flex-wrap">
          <span className="bg-cyan-900 text-cyan-300 border border-cyan-700 px-2 py-0.5 rounded">
            ✏ DESIGN TIME
          </span>
          {agentList.length > 0 && (
            <span className="bg-green-900 text-green-300 border border-green-700 px-2 py-0.5 rounded">
              {approvedCount} approved
            </span>
          )}
          {agentList.length - approvedCount > 0 && (
            <span className="bg-amber-900 text-amber-300 border border-amber-700 px-2 py-0.5 rounded">
              {agentList.length - approvedCount} critiquing
            </span>
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
          💾 Save &amp; Run →
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
