import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { PanelGroup, Panel, PanelResizeHandle } from "react-resizable-panels";
import { useDesignStore } from "../store/runStore";
import { usePipelineStore } from "../store/pipelineStore";
import { useDesignWS } from "../hooks/useDesignWS";
import { getPipeline, updatePipeline, suggestExtensions, api } from "../api/client";
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

/** Modal overlay wrapper */
function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-[#0d1117] border border-gray-700/60 rounded-2xl w-full max-w-lg mx-4 p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-white font-bold font-mono text-base">{title}</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-white text-xl leading-none">✕</button>
        </div>
        {children}
      </div>
    </div>
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
  const { isConnected, events, agents, dag, isComplete, phase, phaseMessage, llmTokens } = useDesignStore();
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [designTrigger, setDesignTrigger] = useState(-1); // -1 = don't auto-start WS

  // Save modal
  const [showSave, setShowSave] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [saving, setSaving] = useState(false);
  const saveInputRef = useRef<HTMLInputElement>(null);

  // Extend modal
  const [showExtend, setShowExtend] = useState(false);
  const [extendObjective, setExtendObjective] = useState("");
  const [extendLoading, setExtendLoading] = useState(false);
  const [extendSuggestions, setExtendSuggestions] = useState<{
    extension_summary: string;
    new_agents: Array<{ agent_id: string; agent_name: string; description: string }>;
    new_edges: Array<{ from: string; to: string; payload_description: string }>;
  } | null>(null);
  const [selectedNewAgents, setSelectedNewAgents] = useState<Set<string>>(new Set());

  const { stop } = useDesignWS(pipelineId ?? null, designTrigger);

  // Pre-fill save name from pipeline
  useEffect(() => {
    if (showSave && activePipeline) setSaveName(activePipeline.name || "");
  }, [showSave, activePipeline]);
  useEffect(() => {
    if (showSave) setTimeout(() => saveInputRef.current?.focus(), 50);
  }, [showSave]);

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

        // Hydrate design store from saved blueprint — no need to re-run LLM
        const blueprint = r.data.blueprint as {
          agents?: Array<{ agent_id: string; agent_name: string; description?: string; [k: string]: unknown }>;
          edges?: Array<{ from: string; to: string; payload_description?: string }>;
        } | null;
        if (blueprint?.agents?.length) {
          const store = useDesignStore.getState();
          store.reset();
          blueprint.agents.forEach((spec) => {
            store.upsertAgent({
              agent_id: spec.agent_id,
              agent_name: spec.agent_name,
              phase: "design_time",
              state: "APPROVED" as const,
              description: (spec.description as string) ?? "",
              input_schema: (spec.input_schema as Record<string, unknown>) ?? {},
              output_schema: (spec.output_schema as Record<string, unknown>) ?? {},
              critique_iterations: 0,
              quality_score: null,
              critique_history: [],
            });
          });
          // Build DAG from blueprint edges
          const nodes = blueprint.agents.map((a) => ({
            node_id: `node_${a.agent_id}`,
            agent_id: a.agent_id,
            agent_name: a.agent_name,
            depends_on: (a.depends_on as string[]) ?? [],
          }));
          const edges = (blueprint.edges ?? []).map((e) => ({
            edge_id: `e_node_${e.from}_node_${e.to}`,
            from_node: `node_${e.from}`,
            to_node: `node_${e.to}`,
          }));
          store.setDAG({ nodes, edges });
          store.setComplete(true);
          store.setPhaseMessage(`Loaded — ${blueprint.agents.length} agents ready`);
        }
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

  // Save handler
  const handleSave = async () => {
    if (!pipelineId || !saveName.trim()) return;
    setSaving(true);
    try {
      const r = await updatePipeline(pipelineId, saveName.trim());
      setActivePipeline(r.data);
      upsertSummary({ id: r.data.id, objective: r.data.objective, name: r.data.name, agent_count: agentList.length, created_at: r.data.created_at });
      setShowSave(false);
    } finally {
      setSaving(false);
    }
  };

  // Extend: ask LLM for suggestions
  const handleExtendSuggest = async () => {
    if (!pipelineId || !extendObjective.trim()) return;
    setExtendLoading(true);
    setExtendSuggestions(null);
    setSelectedNewAgents(new Set());
    try {
      const r = await suggestExtensions(pipelineId, extendObjective.trim());
      setExtendSuggestions(r.data);
      const allIds = new Set((r.data.new_agents as Array<{agent_id:string}>).map((a) => a.agent_id));
      setSelectedNewAgents(allIds); // all selected by default
    } finally {
      setExtendLoading(false);
    }
  };

  // Extend: apply selected agents → re-design with extended objective
  const handleExtendApply = () => {
    if (!extendSuggestions || !pipelineId || !activePipeline) return;
    const picked = extendSuggestions.new_agents.filter((a) => selectedNewAgents.has(a.agent_id));
    if (picked.length === 0) return;
    const addendum = `\n\nEXTENSION — also add these capabilities: ${picked.map((a) => `${a.agent_name}: ${a.description}`).join('; ')}`;
    setShowExtend(false);
    setExtendObjective("");
    setExtendSuggestions(null);
    api.patch(`/api/pipelines/${pipelineId}`, {
      name: activePipeline.name,
      objective: activePipeline.objective + addendum,
    }).then(() => {
      setActivePipeline({ ...activePipeline, objective: activePipeline.objective + addendum });
      setDesignTrigger((t) => t < 0 ? 0 : t + 1);
    }).catch(() => {});
  };

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
            {llmTokens > 0 && (
              <span className="text-gray-500 text-xs font-mono shrink-0">
                · <span className="text-amber-400">{llmTokens.toLocaleString()}</span> tokens
              </span>
            )}
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
          onClick={() => setDesignTrigger((t) => t < 0 ? 0 : t + 1)}
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
          {approvedCount > 0 && <span className="text-green-400 font-bold">✓ {approvedCount}</span>}
          {agentList.length - approvedCount > 0 && isWorking && (
            <span className="text-amber-400 font-bold animate-pulse">● {agentList.length - approvedCount}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* Extend button — available once design is complete */}
          <button
            className={`px-3 py-1.5 rounded-lg font-bold transition-all flex items-center gap-1.5 text-xs ${
              isComplete
                ? "bg-cyan-900/60 hover:bg-cyan-800 text-cyan-300 border border-cyan-700/60"
                : "bg-gray-800/60 text-gray-700 cursor-not-allowed border border-gray-800"
            }`}
            disabled={!isComplete}
            onClick={() => setShowExtend(true)}
            title="Add more agents to extend this pipeline"
          >
            ＋ Extend
          </button>
          {/* Save button */}
          <button
            className={`px-3 py-1.5 rounded-lg font-bold transition-all flex items-center gap-1.5 text-xs ${
              isComplete
                ? "bg-gray-700 hover:bg-gray-600 text-white border border-gray-600"
                : "bg-gray-800/60 text-gray-700 cursor-not-allowed border border-gray-800"
            }`}
            disabled={!isComplete}
            onClick={() => setShowSave(true)}
            title="Save pipeline with a name"
          >
            💾 Save
          </button>
          {/* Run button */}
          <button
            className={`px-4 py-1.5 rounded-lg font-bold transition-all flex items-center gap-2 text-xs ${
              isComplete
                ? "bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-700/30"
                : "bg-gray-800/60 text-gray-700 cursor-not-allowed border border-gray-800"
            }`}
            disabled={!isComplete}
            onClick={() => navigate(`/run/${pipelineId}`)}
            title="Run this pipeline"
          >
            ▶ Run
          </button>
        </div>
      </div>

      <PanelGroup direction="horizontal" className="flex-1 overflow-hidden">
        <Panel defaultSize={22} minSize={14} className="border-r border-gray-800/60 p-3 overflow-hidden">
          <DesignAgentList
            agents={agentList}
            selectedId={selectedAgentId}
            onSelect={setSelectedAgentId}
          />
        </Panel>
        <PanelResizeHandle className="w-1.5 bg-gray-800/60 hover:bg-cyan-700/60 active:bg-cyan-500/60 transition-colors cursor-col-resize" />
        <Panel defaultSize={56} minSize={30} className="p-4 overflow-hidden">
          <CritiqueDetailColumn
            agent={selectedAgent}
            agentIndex={selectedAgentId ? agentList.findIndex((a) => a.agent_id === selectedAgentId) : undefined}
          />
        </Panel>
        <PanelResizeHandle className="w-1.5 bg-gray-800/60 hover:bg-cyan-700/60 active:bg-cyan-500/60 transition-colors cursor-col-resize" />
        <Panel defaultSize={22} minSize={14} className="border-l border-gray-800/60 p-3 overflow-hidden">
          <DagLogColumn
            dag={dag}
            agentStates={agentStates}
            logs={logEntries}
            inputFields={activePipeline?.input_schema ?? []}
            mode="design"
          />
        </Panel>
      </PanelGroup>

      {/* ── Save Modal ─────────────────────────────────────────────────────── */}
      {showSave && (
        <Modal title="💾 Save Pipeline" onClose={() => setShowSave(false)}>
          <p className="text-gray-400 text-sm mb-4">Give this pipeline a name so you can find it later.</p>
          <input
            ref={saveInputRef}
            className="w-full bg-[#161b27] border border-gray-600/60 rounded-lg px-4 py-2.5 text-white font-mono text-sm focus:outline-none focus:border-cyan-500 mb-4"
            placeholder="e.g. Log Topology Analyser v1"
            value={saveName}
            onChange={(e) => setSaveName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && saveName.trim() && handleSave()}
          />
          <div className="flex gap-3 justify-end">
            <button onClick={() => setShowSave(false)} className="px-4 py-2 rounded-lg text-gray-400 hover:text-white text-sm font-mono">Cancel</button>
            <button
              onClick={handleSave}
              disabled={!saveName.trim() || saving}
              className="px-5 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-bold text-sm font-mono transition-colors"
            >
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </Modal>
      )}

      {/* ── Extend Modal ───────────────────────────────────────────────────── */}
      {showExtend && (
        <Modal title="＋ Extend Pipeline" onClose={() => { setShowExtend(false); setExtendSuggestions(null); setExtendObjective(""); }}>
          {!extendSuggestions ? (
            <>
              <p className="text-gray-400 text-sm mb-3">Describe what new capability you want to add to this pipeline.</p>
              <textarea
                className="w-full bg-[#161b27] border border-gray-600/60 rounded-lg px-4 py-2.5 text-white font-mono text-sm focus:outline-none focus:border-cyan-500 mb-4 resize-none"
                rows={3}
                placeholder="e.g. Also generate a Grafana dashboard from the log metrics"
                value={extendObjective}
                onChange={(e) => setExtendObjective(e.target.value)}
              />
              <div className="flex gap-3 justify-end">
                <button onClick={() => setShowExtend(false)} className="px-4 py-2 rounded-lg text-gray-400 hover:text-white text-sm font-mono">Cancel</button>
                <button
                  onClick={handleExtendSuggest}
                  disabled={!extendObjective.trim() || extendLoading}
                  className="px-5 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-bold text-sm font-mono transition-colors flex items-center gap-2"
                >
                  {extendLoading ? <><span className="animate-spin">⟳</span> Asking LLM…</> : "Suggest Agents →"}
                </button>
              </div>
            </>
          ) : (
            <>
              <p className="text-green-400 text-sm font-mono mb-1">✓ {extendSuggestions.extension_summary}</p>
              <p className="text-gray-500 text-xs mb-3">Select which new agents to add:</p>
              <div className="space-y-2 max-h-64 overflow-y-auto mb-4">
                {extendSuggestions.new_agents.map((a) => {
                  const checked = selectedNewAgents.has(a.agent_id);
                  return (
                    <label key={a.agent_id} className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${checked ? "border-cyan-600/60 bg-cyan-900/20" : "border-gray-700/60 bg-[#161b27] hover:border-gray-600"}`}>
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => setSelectedNewAgents((s) => {
                          const next = new Set(s);
                          checked ? next.delete(a.agent_id) : next.add(a.agent_id);
                          return next;
                        })}
                        className="mt-0.5 accent-cyan-500"
                      />
                      <div>
                        <div className="text-white font-mono font-bold text-sm">{a.agent_name}</div>
                        <div className="text-gray-400 text-xs">{a.description}</div>
                      </div>
                    </label>
                  );
                })}
              </div>
              <div className="flex gap-3 justify-between items-center">
                <button onClick={() => setExtendSuggestions(null)} className="text-gray-500 hover:text-gray-300 text-xs font-mono">← Back</button>
                <div className="flex gap-2">
                  <button onClick={() => { setShowExtend(false); setExtendSuggestions(null); }} className="px-4 py-2 rounded-lg text-gray-400 hover:text-white text-sm font-mono">Cancel</button>
                  <button
                    onClick={handleExtendApply}
                    disabled={selectedNewAgents.size === 0}
                    className="px-5 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-bold text-sm font-mono transition-colors"
                  >
                    Add {selectedNewAgents.size} Agent{selectedNewAgents.size !== 1 ? "s" : ""} & Re-design
                  </button>
                </div>
              </div>
            </>
          )}
        </Modal>
      )}
    </div>
  );
}
