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
  }, [pipelineId]);

  // Track running agent from events
  useEffect(() => {
    if (runEvents.length === 0) return;
    const last = runEvents[runEvents.length - 1];
    if (last.type === "AGENT_STARTED" && "agent_id" in last) {
      setRunningAgentId(last.agent_id as string);
      setSelectedAgentId(last.agent_id as string);
    } else if (last.type === "RUN_COMPLETE" || last.type === "ERROR") {
      setRunningAgentId(null);
      setSelectedAgentId(null); // show summary panel
    }
  }, [runEvents]);

  // Elapsed timer
  useEffect(() => {
    if (!startedAt || isComplete) return;
    const t = setInterval(
      () => setElapsed(Math.floor((Date.now() - startedAt) / 1000)),
      1000
    );
    return () => clearInterval(t);
  }, [startedAt, isComplete]);

  const handleStartRun = async () => {
    if (!pipelineId) return;
    const missing = inputSchema.filter(
      (f) => f.required && !inputValues[f.name]?.trim()
    );
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
    ? (activePipeline.blueprint.agents as Array<{
        agent_id: string;
        agent_name: string;
        description?: string;
      }>)
    : [];

  const hasBlueprint = agentList.length > 0;
  const isRunning = !!currentRunId && isConnected && !isComplete;
  const doneCount = Object.values(activeResults).filter(
    (r) => r.status === "completed"
  ).length;
  const failedCount = Object.values(activeResults).filter(
    (r) => r.status === "failed"
  ).length;
  const doneOrFailed = doneCount + failedCount;
  const progress =
    agentList.length > 0 ? Math.round((doneOrFailed / agentList.length) * 100) : 0;

  // Pills
  const pills: StepPill[] = agentList.map((a) => {
    const result = activeResults[a.agent_id];
    const isActiveNow = a.agent_id === runningAgentId;
    const state: StepPill["state"] =
      result?.status === "completed" ? "done" :
      result?.status === "failed"    ? "error" :
      isActiveNow                    ? "active-run" : "pending";
    return {
      id: a.agent_id,
      label: a.agent_name,
      state,
      detail:
        result?.duration_ms
          ? `${result.duration_ms}ms`
          : isActiveNow && elapsed > 0
          ? `${elapsed}s`
          : undefined,
    };
  });

  // Narration
  let narration = "Provide inputs and start a run…";
  let narrationSub: string | undefined;
  if (isComplete) {
    const totalTime = elapsed > 0 ? ` in ${elapsed}s` : "";
    narration =
      failedCount > 0
        ? `⚠ Pipeline finished with ${failedCount} failure${failedCount > 1 ? "s" : ""}${totalTime}`
        : `✓ Pipeline complete${totalTime}`;
  } else if (isRunning && runningAgentId) {
    const spec = agentList.find((a) => a.agent_id === runningAgentId);
    narration = spec ? `Executing ${spec.agent_name}…` : "Executing agent…";
    narrationSub = elapsed > 0 ? `${elapsed}s elapsed` : undefined;
  } else if (isRunning) {
    narration = "Run in progress…";
  }

  // Log entries
  const logEntries = runEvents.map((e) => ({
    type: e.type,
    text: summarizeRunEvent(e as { type: string; [k: string]: unknown }),
  }));

  // Agent state map for DAG
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

  // DAG from blueprint
  const blueprintDag = (activePipeline?.blueprint?.dag as DAGData | undefined) ?? null;

  if (!pipelineId) return null;

  return (
    <div className="flex flex-col h-full bg-gray-950 text-white overflow-hidden">
      {/* Zone 1: Objective banner */}
      <div className="shrink-0 px-4 py-2 border-b border-gray-800 bg-[#120a24] flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-purple-400 text-xs font-mono uppercase tracking-wider shrink-0">
            ▶ Run
          </span>
          <span
            className="text-gray-200 text-sm truncate"
            title={activePipeline?.objective}
          >
            {activePipeline?.name || "Loading…"}
          </span>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <button
            className="text-gray-600 hover:text-cyan-400 text-xs font-mono transition-colors"
            onClick={() => navigate(`/design/${pipelineId}`)}
          >
            ✏ Edit Design
          </button>
          <span
            className={`text-xs font-mono ${
              isComplete
                ? failedCount > 0
                  ? "text-red-400"
                  : "text-green-400"
                : isRunning
                ? "text-purple-400 animate-pulse"
                : "text-gray-600"
            }`}
          >
            {isComplete
              ? failedCount > 0
                ? "✗ Failed"
                : "✓ Complete"
              : isRunning
              ? "● Running"
              : "○ Idle"}
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
        done={doneCount}
        mode={isRunning || isComplete ? "run" : "idle"}
      />

      {/* Zone 3: Status bar */}
      <div className="shrink-0 px-4 py-1.5 border-b border-gray-800 bg-gray-950 flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="bg-purple-900 text-purple-300 border border-purple-700 px-2 py-0.5 rounded">
            ▶ RUN TIME
          </span>
          {doneCount > 0 && (
            <span className="bg-green-900 text-green-300 border border-green-700 px-2 py-0.5 rounded">
              {doneCount} done
            </span>
          )}
          {failedCount > 0 && (
            <span className="bg-red-900 text-red-300 border border-red-700 px-2 py-0.5 rounded">
              {failedCount} failed
            </span>
          )}
          {isRunning && (
            <span className="bg-purple-900 text-purple-300 border border-purple-700 px-2 py-0.5 rounded animate-pulse">
              1 running
            </span>
          )}
          {currentRunId && agentList.length - doneOrFailed - (isRunning ? 1 : 0) > 0 && (
            <span className="bg-gray-800 text-gray-500 border border-gray-700 px-2 py-0.5 rounded">
              {agentList.length - doneOrFailed - (isRunning ? 1 : 0)} waiting
            </span>
          )}
        </div>
        <div className="text-gray-600">
          {elapsed > 0 ? `${elapsed}s elapsed` : ""}
        </div>
      </div>

      {/* Zone 4: 3-column body */}
      {!hasBlueprint ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="text-gray-500 text-sm mb-4">
              This pipeline hasn't been designed yet.
            </div>
            <button
              className="bg-cyan-700 hover:bg-cyan-600 text-white text-sm px-6 py-2 rounded-lg"
              onClick={() => navigate(`/design/${pipelineId}`)}
            >
              ✏️ Design Pipeline First
            </button>
          </div>
        </div>
      ) : (
        <div className="flex-1 grid grid-cols-[220px_1fr_200px] gap-0 overflow-hidden">
          {/* Col 1: Agent list */}
          <div className="border-r border-gray-800 p-3 overflow-hidden">
            <RunAgentList
              agents={agentList}
              results={activeResults}
              runningId={runningAgentId}
              selectedId={selectedAgentId}
              onSelect={setSelectedAgentId}
            />
          </div>

          {/* Col 2: Run detail / input form */}
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
                onInputChange={(name, value) =>
                  setInputValues((v) => ({ ...v, [name]: value }))
                }
                onStartRun={handleStartRun}
                starting={starting}
                hasBlueprint={hasBlueprint}
              />
          </div>

          {/* Col 3: DAG + log */}
          <div className="border-l border-gray-800 p-3 overflow-hidden">
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
