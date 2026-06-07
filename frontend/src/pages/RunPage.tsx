import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useRunStore } from "../store/runStore";
import { usePipelineStore } from "../store/pipelineStore";
import { useRunWS } from "../hooks/useRunWS";
import { getPipeline, createRun } from "../api/client";
import { ProgressStrip, type StepPill } from "../components/ProgressStrip";
import { RunAgentList } from "../components/AgentListColumn";
import { RunDetailColumn } from "../components/RunDetailColumn";
import { DagLogColumn } from "../components/DagLogColumn";
import type { InputField, DAGData } from "../types";

function ThinkingDots() {
  return (
    <span className="inline-flex items-center gap-0.5 ml-1">
      <span className="thinking-dot h-1.5 w-1.5 rounded-full bg-purple-400 inline-block" />
      <span className="thinking-dot h-1.5 w-1.5 rounded-full bg-purple-400 inline-block" />
      <span className="thinking-dot h-1.5 w-1.5 rounded-full bg-purple-400 inline-block" />
    </span>
  );
}

function summarizeRunEvent(event: { type: string; [k: string]: unknown }): string {
  switch (event.type) {
    case "RUN_STARTED":   return `Run started for: ${event.objective ?? event.run_id}`;
    case "AGENT_STARTED": return `Starting: ${event.agent_name}`;
    case "AGENT_RESULT":  return `${event.agent_name} → ${event.status}${event.duration_ms ? ` (${event.duration_ms}ms)` : ""}`;
    case "RUN_COMPLETE":  return `Complete: ${event.completed}/${event.total_agents} agents`;
    case "ERROR":         return `Error: ${event.message}`;
    default:              return (event.message as string) || event.type;
  }
}

export function RunPage() {
  const { pipelineId } = useParams<{ pipelineId: string }>();
  const navigate = useNavigate();
  const { activePipeline, setActivePipeline } = usePipelineStore();
  const { activeResults, runEvents, isConnected, isComplete, setRun } = useRunStore();

  const [inputValues, setInputValues] = useState<Record<string, string>>({});
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [inputSchema, setInputSchema] = useState<InputField[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [runningAgentId, setRunningAgentId] = useState<string | null>(null);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);

  useRunWS(currentRunId);

  useEffect(() => {
    if (!pipelineId) return;
    getPipeline(pipelineId)
      .then((r) => {
        setActivePipeline(r.data);
        setInputSchema(r.data.input_schema || []);
      })
      .catch(() => {});
  }, [pipelineId, setActivePipeline]);

  useEffect(() => {
    if (runEvents.length === 0) return;
    const last = runEvents[runEvents.length - 1];
    if (last.type === "AGENT_STARTED" && "agent_id" in last) {
      setRunningAgentId(last.agent_id as string);
      setSelectedAgentId(last.agent_id as string);
    } else if (last.type === "RUN_COMPLETE" || last.type === "ERROR") {
      setRunningAgentId(null);
      setSelectedAgentId(null);
    }
  }, [runEvents]);

  useEffect(() => {
    if (!startedAt || isComplete) return;
    const t = setInterval(() => setElapsed(Math.floor((Date.now() - startedAt) / 1000)), 1000);
    return () => clearInterval(t);
  }, [startedAt, isComplete]);

  const handleStartRun = async () => {
    if (!pipelineId) return;
    const missing = inputSchema.filter((f) => f.required && !inputValues[f.name]?.trim());
    if (missing.length > 0) {
      alert(`Please provide: ${missing.map((f) => f.name).join(", ")}`);
      return;
    }
    setStarting(true);
    try {
      const { data: newRun } = await createRun(pipelineId, inputValues);
      setRun(newRun);
      setCurrentRunId(newRun.id);
      setStartedAt(Date.now());
      setElapsed(0);
    } catch {
      alert("Failed to start run.");
    } finally {
      setStarting(false);
    }
  };

  const agentList = activePipeline?.blueprint?.agents
    ? (activePipeline.blueprint.agents as Array<{ agent_id: string; agent_name: string; description?: string }>)
    : [];

  const hasBlueprint = agentList.length > 0;
  const isRunning = !!currentRunId && isConnected && !isComplete;
  const doneCount = Object.values(activeResults).filter((r) => r.status === "completed").length;
  const failedCount = Object.values(activeResults).filter((r) => r.status === "failed").length;
  const doneOrFailed = doneCount + failedCount;
  const progress = agentList.length > 0 ? Math.round((doneOrFailed / agentList.length) * 100) : 0;

  const pills: StepPill[] = agentList.map((a) => {
    const result = activeResults[a.agent_id];
    const isActiveNow = a.agent_id === runningAgentId;
    const state: StepPill["state"] =
      result?.status === "completed" ? "done" :
      result?.status === "failed" ? "error" :
      isActiveNow ? "active-run" : "pending";
    return {
      id: a.agent_id,
      label: a.agent_name,
      state,
      detail: result?.duration_ms ? `${result.duration_ms}ms` : isActiveNow && elapsed > 0 ? `${elapsed}s` : undefined,
    };
  });

  let narration = "Provide inputs and start a run…";
  let narrationHighlight: string | undefined;
  let narrationSub: string | undefined;
  if (isComplete) {
    const totalTime = elapsed > 0 ? ` in ${elapsed}s` : "";
    narration = failedCount > 0
      ? `⚠ Pipeline finished with ${failedCount} failure${failedCount > 1 ? "s" : ""}${totalTime}`
      : `✓ Pipeline complete${totalTime}`;
  } else if (isRunning && runningAgentId) {
    const spec = agentList.find((a) => a.agent_id === runningAgentId);
    narration = "Executing";
    narrationHighlight = spec?.agent_name;
    narrationSub = elapsed > 0 ? `${elapsed}s elapsed` : undefined;
  } else if (isRunning) {
    narration = "Run in progress…";
  }

  const logEntries = runEvents.map((e) => ({
    type: e.type,
    text: summarizeRunEvent(e as { type: string; [k: string]: unknown }),
  }));
  const agentStates: Record<string, string> = {};
  agentList.forEach((a) => {
    const result = activeResults[a.agent_id];
    if (result?.status === "completed") agentStates[a.agent_id] = "completed";
    else if (result?.status === "failed") agentStates[a.agent_id] = "failed";
    else if (a.agent_id === runningAgentId) agentStates[a.agent_id] = "running";
    else agentStates[a.agent_id] = "PENDING";
  });

  const selectedResult = selectedAgentId ? activeResults[selectedAgentId] : undefined;
  const selectedSpec = agentList.find((a) => a.agent_id === selectedAgentId);
  const blueprintDag = (activePipeline?.blueprint?.dag as DAGData | undefined) ?? null;

  if (!pipelineId) return null;

  return (
    <div className="flex flex-col h-full bg-[#0a0e1a] text-white overflow-hidden">
      <div className="shrink-0 px-5 pt-3 pb-1 flex items-center gap-3">
        <span className="text-purple-400 text-base">▶</span>
        <span className="text-purple-400 font-bold font-mono tracking-widest text-sm">RUN TIME</span>
        {isRunning && (
          <span className="flex items-center text-xs text-gray-600 font-mono">
            · Executing agents<ThinkingDots />
          </span>
        )}
        {isComplete && (
          <span className={`text-xs font-mono ${failedCount > 0 ? "text-orange-400" : "text-green-500"}`}>
            · {failedCount > 0 ? `Completed with ${failedCount} failure(s)` : "All agents completed"}
          </span>
        )}
      </div>

      <div className="shrink-0 mx-4 mb-2 px-4 py-3 border border-gray-700/50 bg-[#120a24] rounded-xl flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-purple-500 text-sm shrink-0">▶</span>
          <span className="text-purple-500 text-xs font-mono font-bold uppercase tracking-wider shrink-0">Run</span>
          <span className="text-gray-200 text-sm truncate font-mono" title={activePipeline?.objective}>
            {activePipeline?.name || "Loading…"}
          </span>
        </div>
        <button
          className="text-gray-500 hover:text-cyan-400 text-xs font-mono transition-colors"
          onClick={() => navigate(`/design/${pipelineId}`)}
        >
          ✏ Edit Design
        </button>
      </div>

      <ProgressStrip
        narration={narration}
        narrationHighlight={narrationHighlight}
        narrationSub={narrationSub}
        pills={pills}
        progress={progress}
        total={agentList.length}
        done={doneCount}
        mode={isRunning || isComplete ? "run" : "idle"}
      />

      <div className="shrink-0 px-5 py-1.5 border-b border-gray-800/60 bg-[#0a0e1a] flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="bg-purple-900/50 text-purple-300 border border-purple-700/50 px-2 py-0.5 rounded font-bold">▶ RUN TIME</span>
          {doneCount > 0 && <span className="bg-green-900/50 text-green-300 border border-green-800/50 px-2 py-0.5 rounded">{doneCount} done</span>}
          {failedCount > 0 && <span className="bg-red-900/50 text-red-300 border border-red-800/50 px-2 py-0.5 rounded">{failedCount} failed</span>}
          {isRunning && <span className="bg-purple-900/50 text-purple-300 border border-purple-700/50 px-2 py-0.5 rounded animate-pulse">1 running</span>}
        </div>
        <div className="text-gray-600">{elapsed > 0 ? `${elapsed}s elapsed` : ""}</div>
      </div>

      {!hasBlueprint ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="text-gray-500 text-sm mb-4">This pipeline hasn't been designed yet.</div>
            <button
              className="bg-cyan-700 hover:bg-cyan-600 text-white text-sm px-6 py-2 rounded-lg"
              onClick={() => navigate(`/design/${pipelineId}`)}
            >
              ✏️ Design Pipeline First
            </button>
          </div>
        </div>
      ) : (
        <div className="flex-1 grid grid-cols-[280px_1fr_240px] gap-0 overflow-hidden">
          <div className="border-r border-gray-800/60 p-3 overflow-hidden">
            <RunAgentList
              agents={agentList}
              results={activeResults}
              runningId={runningAgentId}
              selectedId={selectedAgentId}
              onSelect={setSelectedAgentId}
            />
          </div>
          <div className="p-4 overflow-hidden">
            <RunDetailColumn
              agentId={selectedAgentId}
              agentName={selectedSpec?.agent_name}
              agentDescription={selectedSpec?.description}
              result={selectedResult}
              isRunning={selectedAgentId === runningAgentId && isRunning}
              isComplete={isComplete}
              allResults={activeResults}
              userInputs={inputValues}
              inputSchema={inputSchema}
              onInputChange={(name, value) => setInputValues((v) => ({ ...v, [name]: value }))}
              onStartRun={handleStartRun}
              starting={starting}
              hasBlueprint={hasBlueprint}
            />
          </div>
          <div className="border-l border-gray-800/60 p-3 overflow-hidden">
            <DagLogColumn
              dag={blueprintDag}
              agentStates={agentStates}
              logs={logEntries}
              inputFields={inputSchema}
              mode="run"
            />
          </div>
        </div>
      )}
    </div>
  );
}
