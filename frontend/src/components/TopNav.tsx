import { useNavigate, useLocation, useParams } from "react-router-dom";
import { useDesignStore, useRunStore } from "../store/runStore";

export function TopNav() {
  const navigate = useNavigate();
  const location = useLocation();
  const { pipelineId } = useParams<{ pipelineId?: string }>();
  const { llmTokens, phase, isConnected: designConnected, isComplete: designComplete } = useDesignStore();
  const { isConnected: runConnected, isComplete: runComplete, activeResults } = useRunStore();

  const isDesignRoute = location.pathname.startsWith("/design/");
  const isRunRoute = location.pathname.startsWith("/run/");
  const isPipelinesRoute = !isDesignRoute && !isRunRoute;

  const canDesign = !!pipelineId;
  const canRun = !!pipelineId;

  const isDesigning = designConnected && !designComplete;
  const isRunning = runConnected && !runComplete;
  const doneRunCount = Object.values(activeResults).filter((r) => r.status === "completed").length;
  const totalRunCount = Object.keys(activeResults).length;

  function tabCls(active: boolean, disabled: boolean, accent: string) {
    if (disabled) return "px-4 h-full flex items-center text-xs font-mono text-gray-700 cursor-not-allowed select-none";
    return `px-4 h-full flex items-center text-xs font-mono transition-colors cursor-pointer ${
      active
        ? `border-b-2 ${accent} font-bold`
        : "text-gray-500 hover:text-gray-200"
    }`;
  }

  return (
    <div className="shrink-0 h-10 bg-[#080c16] border-b border-gray-800/60 flex items-center z-10">
      <button
        className="px-4 h-full flex items-center text-cyan-400 font-bold text-sm font-mono hover:text-cyan-300 transition-colors shrink-0 border-r border-gray-800/60"
        onClick={() => navigate("/")}
      >
        ⬡
      </button>

      <div className="flex h-full items-stretch">
        <button
          className={tabCls(isPipelinesRoute, false, "border-b-cyan-400 text-cyan-300")}
          onClick={() => navigate("/")}
        >
          ☰ Pipelines
        </button>

        <button
          className={tabCls(isDesignRoute, !canDesign, "border-b-orange-400 text-orange-300")}
          onClick={() => canDesign && navigate(`/design/${pipelineId}`)}
          title={!canDesign ? "Select a pipeline first" : undefined}
        >
          ✏ Design
          {isDesigning && (
            <span className="ml-1.5 h-1.5 w-1.5 rounded-full bg-orange-400 animate-pulse inline-block" />
          )}
        </button>

        <button
          className={tabCls(isRunRoute, !canRun, "border-b-green-400 text-green-300")}
          onClick={() => canRun && navigate(`/run/${pipelineId}`)}
          title={!canRun ? "Select a pipeline first" : undefined}
        >
          ▶ Run
          {isRunning && (
            <span className="ml-1.5 h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse inline-block" />
          )}
        </button>
      </div>

      <div className="flex-1" />
      <div className="px-4 flex items-center gap-3 text-xs font-mono">
        {isDesigning && llmTokens > 0 && (
          <span className="bg-amber-900/40 border border-amber-700/50 text-amber-300 px-2 py-0.5 rounded">
            🟡 {phase} · {llmTokens.toLocaleString()} tokens
          </span>
        )}
        {isRunning && totalRunCount > 0 && (
          <span className="bg-green-900/40 border border-green-700/50 text-green-300 px-2 py-0.5 rounded">
            ▶ {doneRunCount}/{totalRunCount} agents
          </span>
        )}
      </div>
    </div>
  );
}
