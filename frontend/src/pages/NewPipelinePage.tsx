import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createPipeline } from "../api/client";
import { usePipelineStore } from "../store/pipelineStore";

const EXAMPLES = [
  "Analyze my GitHub repository for security vulnerabilities and generate a remediation report",
  "Monitor application logs, identify errors, and create automated remediation scripts",
  "Audit financial transactions for compliance and flag suspicious activity",
];

export function NewPipelinePage() {
  const [objective, setObjective] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { upsertSummary } = usePipelineStore();

  const handleCreate = async () => {
    if (!objective.trim()) return;
    setLoading(true);
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
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center bg-gray-950 p-8">
      <div className="w-full max-w-xl">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-cyan-400 mb-2 font-mono">New Pipeline</h1>
          <p className="text-gray-400 text-sm">
            Describe your objective — AgentMaster will design the full agent pipeline for you.
          </p>
        </div>

        <div className="bg-gray-900 border border-gray-700 rounded-lg p-6">
          <label className="block text-sm text-gray-300 mb-2 font-mono">Objective</label>
          <textarea
            className="w-full bg-gray-800 border border-gray-600 text-white px-4 py-3 rounded-lg text-sm resize-none focus:outline-none focus:border-cyan-500 transition-colors font-mono"
            rows={4}
            placeholder="Describe any objective…"
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && e.ctrlKey) handleCreate();
            }}
          />

          <div className="mt-2 flex gap-2 flex-wrap">
            {EXAMPLES.map((ex, i) => (
              <button
                key={i}
                className="text-xs text-gray-500 hover:text-cyan-400 underline font-mono"
                onClick={() => setObjective(ex)}
              >
                Example {i + 1}
              </button>
            ))}
          </div>

          <button
            className="mt-4 w-full bg-cyan-700 hover:bg-cyan-600 text-white font-bold py-3 rounded-lg text-sm transition-colors disabled:opacity-50 font-mono"
            onClick={handleCreate}
            disabled={loading || !objective.trim()}
          >
            {loading ? "Creating…" : "✏️ Design Pipeline"}
          </button>
        </div>

        <div className="text-center mt-6 text-gray-600 text-xs font-mono">
          Ctrl+Enter to submit
        </div>
      </div>
    </div>
  );
}
