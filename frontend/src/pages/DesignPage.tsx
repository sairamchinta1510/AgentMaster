import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { PanelGroup, Panel, PanelResizeHandle } from "react-resizable-panels";
import { useDesignStore } from "../store/runStore";
import { usePipelineStore } from "../store/pipelineStore";
import { useDesignWS } from "../hooks/useDesignWS";
import { getPipeline, updatePipeline, suggestExtensions } from "../api/client";
import { ProgressStrip, type StepPill } from "../components/ProgressStrip";
import { DesignAgentList } from "../components/AgentListColumn";
import { CritiqueDetailColumn } from "../components/CritiqueDetailColumn";
import { DagLogColumn } from "../components/DagLogColumn";
import { useExtendWS } from "../hooks/useExtendWS";
import type { AtomicAgent } from "../types";

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
  const { isConnected, events, agents, dag, isComplete, phase } = useDesignStore();
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

  // Extend WS
  const [extendTrigger, setExtendTrigger] = useState(-1);
  const [extendPayload, setExtendPayload] = useState<{
    new_agents: Array<{ agent_id: string; agent_name: string; [k: string]: unknown }>;
    new_edges: Array<{ from: string; to: string; payload_description?: string }>;
  } | null>(null);

  const { stop } = useDesignWS(pipelineId ?? null, designTrigger);

  // onExtendComplete: re-hydrate store from the merged blueprint returned by WS
  const handleExtendComplete = useCallback((blueprint: Record<string, unknown>) => {
    const agents = blueprint.agents as Array<{ agent_id: string; agent_name: string; description?: string; depends_on?: string[]; [k:string]: unknown }> ?? [];
    const edges = blueprint.edges as Array<{ from: string; to: string }> ?? [];
    const store = useDesignStore.getState();
    store.reset();
    agents.forEach((spec) => {
      store.upsertAgent({
        agent_id: spec.agent_id,
        agent_name: spec.agent_name,
        phase: "design_time",
        state: "APPROVED" as const,
        description: spec.description ?? "",
        input_schema: (spec.input_schema as Record<string, unknown>) ?? {},
        output_schema: (spec.output_schema as Record<string, unknown>) ?? {},
        critique_iterations: 0,
        quality_score: null,
        critique_history: [],
      });
    });
    store.setDAG({
      nodes: agents.map((a) => ({ node_id: `node_${a.agent_id}`, agent_id: a.agent_id, agent_name: a.agent_name, depends_on: a.depends_on ?? [] })),
      edges: edges.map((e) => ({ edge_id: `e_node_${e.from}_node_${e.to}`, from_node: `node_${e.from}`, to_node: `node_${e.to}` })),
    });
    store.setComplete(true);
  }, []);

  useExtendWS(pipelineId ?? null, extendTrigger, extendPayload, handleExtendComplete);

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

  // Extend: apply selected agents → run ONLY new agents through produce+critique WS
  const handleExtendApply = () => {
    if (!extendSuggestions || !pipelineId) return;
    const picked = extendSuggestions.new_agents.filter((a) => selectedNewAgents.has(a.agent_id));
    const pickedEdges = extendSuggestions.new_edges.filter(
      (e) => picked.some((a) => a.agent_id === e.to || a.agent_id === e.from)
    );
    if (picked.length === 0) return;
    setShowExtend(false);
    setExtendObjective("");
    setExtendSuggestions(null);
    // Fire extend WS — only the picked agents go through produce+critique
    setExtendPayload({ new_agents: picked, new_edges: pickedEdges });
    setExtendTrigger((t) => t < 0 ? 0 : t + 1);
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
      {/* Context bar */}
      <div className="shrink-0 border-b border-gray-800/60 bg-[#0d1117] px-5 py-2 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-white font-bold text-sm font-mono truncate">
            {activePipeline?.name || "Untitled Pipeline"}
          </span>
          <span className="text-gray-700 shrink-0">·</span>
          <span className="text-gray-500 text-xs font-mono truncate" title={activePipeline?.objective}>
            {activePipeline?.objective || "Loading…"}
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            className={`px-3 py-1.5 rounded-lg font-bold text-xs font-mono transition-all ${
              isWorking
                ? "bg-gray-800 text-gray-600 cursor-not-allowed"
                : "bg-cyan-900/50 hover:bg-cyan-800 text-cyan-300 border border-cyan-700/60"
            }`}
            onClick={() => setDesignTrigger((t) => t < 0 ? 0 : t + 1)}
            disabled={isWorking}
          >
            {isWorking ? <span className="animate-pulse">⟳ Designing…</span> : isComplete ? "↺ Re-design" : "✏ Design"}
          </button>
          {isWorking && (
            <button
              className="px-3 py-1.5 rounded-lg font-bold text-xs font-mono bg-red-900/50 hover:bg-red-800 text-red-300 border border-red-700/60 transition-all"
              onClick={stop}
            >
              ⏹ Stop
            </button>
          )}
          <button
            className={`px-3 py-1.5 rounded-lg font-bold text-xs font-mono transition-all ${
              isComplete
                ? "bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700"
                : "bg-gray-900 text-gray-700 cursor-not-allowed border border-gray-800"
            }`}
            disabled={!isComplete}
            onClick={() => setShowExtend(true)}
          >
            ＋ Extend
          </button>
          <button
            className={`px-3 py-1.5 rounded-lg font-bold text-xs font-mono transition-all ${
              isComplete
                ? "bg-gray-800 hover:bg-gray-700 text-white border border-gray-700"
                : "bg-gray-900 text-gray-700 cursor-not-allowed border border-gray-800"
            }`}
            disabled={!isComplete}
            onClick={() => setShowSave(true)}
          >
            💾 Save
          </button>
          <button
            className={`px-4 py-1.5 rounded-lg font-bold text-xs font-mono transition-all ${
              isComplete
                ? "bg-green-700 hover:bg-green-600 text-white shadow-lg shadow-green-900/30"
                : "bg-gray-900 text-gray-700 cursor-not-allowed border border-gray-800"
            }`}
            disabled={!isComplete}
            onClick={() => navigate(`/run/${pipelineId}`)}
          >
            ▶ Run
          </button>
        </div>
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
