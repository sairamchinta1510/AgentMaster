import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { createPipeline, listPipelines, deletePipeline } from "../api/client";
import { usePipelineStore } from "../store/pipelineStore";
import type { PipelineSummary } from "../types";

function StatusBadge({ agentCount }: { agentCount: number }) {
  if (agentCount > 0) {
    return (
      <span className="text-xs px-2 py-0.5 rounded-full bg-blue-900/50 border border-blue-700/50 text-blue-300 font-mono">
        Designed · {agentCount} agents
      </span>
    );
  }
  return (
    <span className="text-xs px-2 py-0.5 rounded-full bg-gray-800 border border-gray-700 text-gray-500 font-mono">
      Not yet designed
    </span>
  );
}

const EXAMPLES = [
  "Analyze my GitHub repository for security vulnerabilities and generate a remediation report",
  "Monitor application logs, identify errors, and create automated remediation scripts",
];

export function PipelinesPage() {
  const navigate = useNavigate();
  const { pipelines, setPipelines, upsertSummary, removePipeline } = usePipelineStore();
  const [showCreate, setShowCreate] = useState(false);
  const [objective, setObjective] = useState("");
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setFetchError(null);
    listPipelines()
      .then((r) => setPipelines(r.data))
      .catch(() => setFetchError("Could not load pipelines. Check your connection and refresh."))
      .finally(() => setLoading(false));
  }, [setPipelines]);

  const handleCreate = async () => {
    if (!objective.trim()) return;
    setCreating(true);
    try {
      const { data } = await createPipeline(objective.trim());
      upsertSummary({
        id: data.id,
        objective: data.objective,
        name: data.name,
        agent_count: 0,
        created_at: data.created_at,
      });
      navigate(`/design/${data.id}`);
    } catch {
      alert("Failed to create pipeline.");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!confirm("Delete this pipeline?")) return;
    try {
      await deletePipeline(id);
      removePipeline(id);
    } catch {
      alert("Failed to delete.");
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-[#0a0e1a]">
      <div className="max-w-3xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-white font-bold text-xl font-mono">My Pipelines</h1>
            <p className="text-gray-500 text-sm mt-0.5">AI agent pipelines built with AAGF</p>
          </div>
          <button
            className="bg-cyan-700 hover:bg-cyan-600 text-white font-bold px-4 py-2 rounded-lg text-sm font-mono transition-colors flex items-center gap-2"
            onClick={() => { setShowCreate((v) => !v); setObjective(""); }}
          >
            {showCreate ? "✕ Cancel" : "＋ New Pipeline"}
          </button>
        </div>

        {showCreate && (
          <div className="bg-[#0d1117] border border-cyan-800/50 rounded-xl p-5 mb-6">
            <label className="block text-sm text-gray-300 mb-2 font-mono">Objective</label>
            <textarea
              autoFocus
              className="w-full bg-gray-800 border border-gray-700 text-white px-4 py-3 rounded-lg text-sm resize-none focus:outline-none focus:border-cyan-500 transition-colors font-mono"
              rows={3}
              placeholder="Describe any software development or observability objective…"
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && e.ctrlKey) handleCreate(); }}
            />
            <div className="mt-2 mb-3 flex gap-2 flex-wrap">
              {EXAMPLES.map((ex, i) => (
                <button
                  key={i}
                  className="text-xs text-gray-600 hover:text-cyan-400 underline font-mono"
                  onClick={() => setObjective(ex)}
                >
                  Example {i + 1}
                </button>
              ))}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600 text-xs font-mono">Ctrl+Enter to submit</span>
              <button
                className="bg-cyan-700 hover:bg-cyan-600 disabled:bg-gray-700 disabled:text-gray-500 text-white font-bold py-2 px-6 rounded-lg text-sm transition-colors font-mono"
                onClick={handleCreate}
                disabled={creating || !objective.trim()}
              >
                {creating ? "Creating…" : "✏ Design Pipeline"}
              </button>
            </div>
          </div>
        )}

        {loading && (
          <div className="text-center py-16 text-gray-600">
            <div className="text-sm font-mono animate-pulse">Loading pipelines…</div>
          </div>
        )}

        {!loading && fetchError && (
          <div className="bg-red-950/40 border border-red-800/50 rounded-xl p-4 text-red-400 text-sm font-mono">
            ⚠ {fetchError}
          </div>
        )}

        {!loading && !fetchError && pipelines.length === 0 && !showCreate && (
          <div className="text-center py-16 text-gray-600">
            <div className="text-4xl mb-3">⬡</div>
            <div className="text-sm font-mono">No pipelines yet.</div>
            <button
              className="mt-3 text-cyan-500 underline text-sm font-mono"
              onClick={() => setShowCreate(true)}
            >
              Create your first pipeline
            </button>
          </div>
        )}

        {!loading && !fetchError && (
          <div className="space-y-2">
            {pipelines.map((p: PipelineSummary) => (
              <div
                key={p.id}
                className="group bg-[#0d1117] border border-gray-800 hover:border-gray-700 rounded-xl px-5 py-4 cursor-pointer transition-all"
                onClick={() => navigate(`/design/${p.id}`)}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1 flex-wrap">
                      <span className="text-white font-bold font-mono text-sm">{p.name}</span>
                      <StatusBadge agentCount={p.agent_count} />
                    </div>
                    <div className="text-gray-500 text-xs font-mono truncate">{p.objective}</div>
                    {p.created_at && (
                      <div className="text-gray-700 text-xs mt-1">
                        {new Date(p.created_at).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2 shrink-0 items-center">
                    <button
                      className="opacity-0 group-hover:opacity-100 bg-[#161b22] hover:bg-cyan-900/40 border border-gray-700 hover:border-cyan-700 text-gray-400 hover:text-cyan-300 text-xs font-bold px-3 py-1.5 rounded-lg font-mono transition-all"
                      onClick={(e) => { e.stopPropagation(); navigate(`/design/${p.id}`); }}
                    >
                      ✏ Design
                    </button>
                    <button
                      className="opacity-0 group-hover:opacity-100 bg-[#161b22] hover:bg-green-900/40 border border-gray-700 hover:border-green-700 text-gray-400 hover:text-green-300 text-xs font-bold px-3 py-1.5 rounded-lg font-mono transition-all"
                      onClick={(e) => { e.stopPropagation(); navigate(`/run/${p.id}`); }}
                    >
                      ▶ Run
                    </button>
                    <button
                      className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-red-400 text-xs px-2 py-1.5 rounded-lg transition-all"
                      onClick={(e) => handleDelete(e, p.id)}
                      title="Delete"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
