import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { listPipelines, deletePipeline } from "../api/client";
import { usePipelineStore } from "../store/pipelineStore";

export function Sidebar() {
  const navigate = useNavigate();
  const { pipelineId } = useParams<{ pipelineId?: string }>();
  const { pipelines, setPipelines, removePipeline } = usePipelineStore();

  useEffect(() => {
    listPipelines()
      .then((r) => setPipelines(r.data))
      .catch(() => {});
  }, []);

  const handleNewPipeline = () => navigate("/");

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!confirm("Delete this pipeline?")) return;
    try {
      await deletePipeline(id);
      removePipeline(id);
      if (pipelineId === id) navigate("/");
    } catch {
      alert("Failed to delete pipeline.");
    }
  };

  return (
    <aside className="w-64 shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-800">
        <div className="text-cyan-400 font-bold text-sm font-mono">⬡ AgentMaster</div>
        <div className="text-gray-500 text-xs mt-0.5">v2 — AAGF</div>
      </div>

      {/* New pipeline button */}
      <div className="px-3 py-2 border-b border-gray-800">
        <button
          className="w-full bg-cyan-700 hover:bg-cyan-600 text-white text-xs font-bold py-2 rounded-lg font-mono transition-colors"
          onClick={handleNewPipeline}
        >
          ✏️ New Pipeline
        </button>
      </div>

      {/* Pipeline list */}
      <div className="flex-1 overflow-y-auto">
        {pipelines.length === 0 && (
          <div className="text-gray-600 text-xs text-center py-8 px-4">
            No pipelines yet.{" "}
            <button className="text-cyan-500 underline" onClick={handleNewPipeline}>
              Create one
            </button>
          </div>
        )}
        {pipelines.map((p) => (
          <div
            key={p.id}
            className={`group px-3 py-2.5 border-b border-gray-800 cursor-pointer hover:bg-gray-800 transition-colors ${
              pipelineId === p.id ? "bg-gray-800 border-l-2 border-l-cyan-500" : ""
            }`}
            onClick={() => navigate(`/design/${p.id}`)}
          >
            <div className="flex items-start justify-between gap-1">
              <div className="flex-1 min-w-0">
                <div className="text-white text-xs font-bold truncate font-mono">{p.name}</div>
                <div className="text-gray-500 text-xs mt-0.5 line-clamp-1">{p.objective}</div>
                <div className="flex items-center gap-2 mt-1">
                  {p.agent_count > 0 && (
                    <span className="text-gray-600 text-xs">{p.agent_count} agents</span>
                  )}
                  {p.created_at && (
                    <span className="text-gray-700 text-xs">
                      {new Date(p.created_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
              {/* Action buttons */}
              <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                <button
                  className="text-xs text-cyan-500 hover:text-cyan-300 p-1"
                  title="Run pipeline"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/run/${p.id}`);
                  }}
                >
                  ▶
                </button>
                <button
                  className="text-xs text-red-600 hover:text-red-400 p-1"
                  title="Delete pipeline"
                  onClick={(e) => handleDelete(e, p.id)}
                >
                  ✕
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
