import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { listPipelines } from "../api/client";
import { usePipelineStore } from "../store/pipelineStore";

export function TopNav() {
  const navigate = useNavigate();
  const { pipelineId } = useParams<{ pipelineId?: string }>();
  const { pipelines, setPipelines } = usePipelineStore();

  useEffect(() => {
    listPipelines()
      .then((r) => setPipelines(r.data))
      .catch(() => {});
  }, [setPipelines]);

  return (
    <div className="shrink-0 h-10 bg-[#080c16] border-b border-gray-800/60 flex items-center px-5 gap-4 z-10">
      <button
        className="text-cyan-400 font-bold text-sm font-mono flex items-center gap-1.5 hover:text-cyan-300 transition-colors shrink-0"
        onClick={() => navigate("/")}
      >
        ⬡ <span className="tracking-wide">AgentMaster</span>
      </button>
      <div className="w-px h-5 bg-gray-800 shrink-0" />
      <div className="flex items-center gap-2 min-w-0">
        {pipelines.length > 0 ? (
          <select
            className="bg-transparent border-0 text-gray-400 text-xs font-mono focus:outline-none cursor-pointer max-w-sm hover:text-gray-200 transition-colors"
            value={pipelineId ?? ""}
            onChange={(e) => {
              if (e.target.value) navigate(`/design/${e.target.value}`);
            }}
          >
            <option value="">— select pipeline —</option>
            {pipelines.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        ) : (
          <span className="text-gray-700 text-xs font-mono">No pipelines yet</span>
        )}
      </div>
      <div className="flex-1" />
      <button
        className="bg-cyan-800/80 hover:bg-cyan-700 text-cyan-200 text-xs font-bold px-3 py-1.5 rounded-lg font-mono transition-colors border border-cyan-700/50"
        onClick={() => navigate("/")}
      >
        ✏ New Pipeline
      </button>
    </div>
  );
}
