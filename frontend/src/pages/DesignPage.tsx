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

function ThinkingDots() {
  return (
    <span className="inline-flex items-center gap-0.5 ml-1">
      <span className="thinking-dot h-1.5 w-1.5 rounded-full bg-orange-400 inline-block" />
      <span className="thinking-dot h-1.5 w-1.5 rounded-full bg-orange-400 inline-block" />
      <span className="thinking-dot h-1.5 w-1.5 rounded-full bg-orange-400 inline-block" />
    </span>
  );
}

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
  const { isConnected, events, agents, dag, isComplete, phase, phaseMessage } = useDesignStore();
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [designTrigger, setDesignTrigger] = useState(0);

  const { stop } = useDesignWS(pipelineId ?? null, designTrigger);

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
  }, [pipelineId, setActivePipeline, upsertSummary]);

  const agentList: AtomicAgent[] = Object.values(agents);
  const approvedCount = agentList.filter(
    (a) => a.state === "APPROVED" || a.state === "COMPLETED"
  ).length;

  useEffect(() => {
    if (selectedAgentId) return;
    const active = agentList.find(
      (a) => a.state !== "PENDING" && a.state !== "APPROVED" && a.state !== "COMPLETED"
    );
    const target = active ?? agentList[0];
    if (target) setSelectedAgentId(target.agent_id);
  }, [agentList, selectedAgentId]);

  const pills: StepPill[] = agentList.map((a) => {
    const isCritiquing =
      a.state.startsWith("DESIGN_CRITIQUE") ||
      a.state === "REVISING_SPEC" ||
      a.state === "AUTO_FIX";
    const roundNum = a.state.startsWith("DESIGN_CRITIQUE") ? a.state.slice(-1) : null;
    const isDone = a.state === "APPROVED" || a.state === "COMPLETED";
    const isErr = a.state === "FAILED_ESCALATED";
    return {
      id: a.agent_id,
      label: a.agent_name,
      state: isDone ? "done" : isErr ? "error" :
        isCritiquing || a.state === "SPECIFYING" ? "active-design" : "pending",
      detail: isCritiquing && roundNum ? `r${roundNum}/5` : undefined,
    };
  });

  const activeAgent = agentList.find(
    (a) => a.state !== "PENDING" && a.state !== "APPROVED" && a.state !== "COMPLETED"
  );
  let narration = "Waiting to start…";
  let narrationHighlight: string | undefined;
  let narrationSub: string | undefined;
  if (isComplete) {
    narration = `✓ All ${approvedCount} agents approved`;
  } else if (activeAgent) {
    const isCritiquing = activeAgent.state.startsWith("DESIGN_CRITIQUE");
    const roundNum = isCritiquing ? activeAgent.state.slice(-1) : null;
    if (isCritiquing) {
      narration = "Critiquing";
      narrationHighlight = activeAgent.agent_name;
      narrationSub = `round ${roundNum} of 5`;
    } else if (activeAgent.state === "REVISING_SPEC" || activeAgent.state === "AUTO_FIX") {
      narration = "Auto-fixing";
      narrationHighlight = activeAgent.agent_name;
    } else if (activeAgent.state === "SPECIFYING") {
      narration = "Designing";
      narrationHighlight = activeAgent.agent_name;
    } else {
      narration = `${activeAgent.agent_name} — ${activeAgent.state}`;
    }
    const latestCritique = activeAgent.critique_history?.[activeAgent.critique_history.length - 1];
    if (latestCritique && (latestCritique.issues ?? []).length > 0) {
      narrationSub = `Auto-fixing: ${(latestCritique.issues ?? []).slice(0, 2).map((i) => i.category).join(" · ")}`;
    }
  } else if (isConnected && phase) {
    narration = phase;
  }

  const progress = agentList.length > 0 ? Math.round((approvedCount / agentList.length) * 100) : 0;
  const logEntries = events.map((e) => ({
    type: e.type,
    text: summarizeEvent(e as { type: string; [k: string]: unknown }),
  }));
  const agentStates: Record<string, string> = {};
  agentList.forEach((a) => { agentStates[a.agent_id] = a.state; });
  const selectedAgent = selectedAgentId ? (agents[selectedAgentId] ?? null) : null;

  if (!pipelineId) return null;

  const isWorking = isConnected && !isComplete;

  return (
    <div className="flex flex-col h-full bg-[#0a0e1a] text-white overflow-hidden">
      <div className="shrink-0 px-5 pt-3 pb-1 flex items-center gap-3">
        <span className="text-orange-400 text-base">🔥</span>
        <span className="text-orange-400 font-bold font-mono tracking-widest text-sm shrink-0">DESIGN TIME</span>
        {isWorking && (
          <>
            <span className="text-gray-700 font-mono text-xs shrink-0">·</span>
            <span className="text-cyan-300 text-xs font-mono truncate">
              {phaseMessage || "AI is working…"}
            </span>
            <ThinkingDots />
            <button
              className="ml-auto shrink-0 flex items-center gap-1.5 bg-red-900/50 hover:bg-red-800 text-red-300 border border-red-700/60 text-xs font-bold px-3 py-1 rounded-lg font-mono transition-colors"
              onClick={stop}
              title="Stop design process"
            >
              ⏹ Stop
            </button>
          </>
        )}
        {isComplete && (
          <span className="text-xs text-green-500 font-mono">· {phaseMessage || "Blueprint complete"}</span>
        )}
        {!isWorking && !isComplete && phaseMessage && (
          <span className="text-xs text-gray-600 font-mono truncate">· {phaseMessage}</span>
        )}
      </div>

      <div className="shrink-0 mx-4 mb-2 px-4 py-3 border border-gray-700/50 bg-[#0d1117] rounded-xl flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-cyan-500 text-sm shrink-0">○</span>
          <span className="text-cyan-500 text-xs font-mono font-bold uppercase tracking-wider shrink-0">Objective</span>
          <span className="text-gray-200 text-sm truncate font-mono" title={activePipeline?.objective}>
            {activePipeline?.objective || "Loading…"}
          </span>
        </div>
        <button
          className={`font-bold px-5 py-2 rounded-lg text-sm font-mono transition-all shrink-0 flex items-center gap-2 ${
            isWorking
              ? "bg-gray-700 text-gray-500 cursor-not-allowed"
              : "bg-cyan-500 hover:bg-cyan-400 text-[#0a0e1a] shadow-lg shadow-cyan-500/20"
          }`}
          onClick={() => setDesignTrigger((t) => t + 1)}
          disabled={isWorking}
        >
          ✏ {isComplete ? "Re-design" : "Design"}
        </button>
      </div>

      <ProgressStrip
        narration={narration}
        narrationHighlight={narrationHighlight}
        narrationSub={narrationSub}
        pills={pills}
        progress={progress}
        total={agentList.length}
        done={approvedCount}
        mode={isComplete || isConnected ? "design" : "idle"}
      />

      <div className="shrink-0 px-5 py-1.5 border-b border-gray-800/60 bg-[#0a0e1a] flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-3">
          <span className="bg-cyan-900/50 text-cyan-400 border border-cyan-800/60 px-2 py-0.5 rounded font-bold">
            — DESIGN
          </span>
          <span className="text-gray-600">
            {isComplete ? "Blueprint complete" : isWorking ? "Blueprint in progress…" : "Ready to design"}
          </span>
        </div>
        <div className="flex items-center gap-3">
          {approvedCount > 0 && (
            <span className="text-green-400 font-bold">✓ {approvedCount}</span>
          )}
          {agentList.length - approvedCount > 0 && isWorking && (
            <span className="text-amber-400 font-bold animate-pulse">● {agentList.length - approvedCount}</span>
          )}
          <button
            className={`px-4 py-1.5 rounded-lg font-bold transition-all flex items-center gap-2 ${
              isComplete
                ? "bg-purple-700 hover:bg-purple-600 text-white shadow-lg shadow-purple-700/20"
                : "bg-gray-800 text-gray-600 cursor-not-allowed"
            }`}
            disabled={!isComplete}
            onClick={() => navigate(`/run/${pipelineId}`)}
          >
            💜 Save Plan
          </button>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-[280px_1fr_240px] gap-0 overflow-hidden">
        <div className="border-r border-gray-800/60 p-3 overflow-hidden">
          <DesignAgentList
            agents={agentList}
            selectedId={selectedAgentId}
            onSelect={setSelectedAgentId}
          />
        </div>
        <div className="p-4 overflow-hidden">
          <CritiqueDetailColumn
            agent={selectedAgent}
            agentIndex={selectedAgentId ? agentList.findIndex((a) => a.agent_id === selectedAgentId) : undefined}
          />
        </div>
        <div className="border-l border-gray-800/60 p-3 overflow-hidden">
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
