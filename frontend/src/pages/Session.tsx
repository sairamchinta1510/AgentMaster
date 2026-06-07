import { useParams } from "react-router-dom";
import { useSessionStore } from "../store/sessionStore";
import { useWebSocket } from "../hooks/useWebSocket";
import { PhaseIndicator } from "../components/PhaseIndicator";
import { AgentCard } from "../components/AgentCard";
import { DAGVisualization } from "../components/DAGVisualization";
import { ExecutionLog } from "../components/ExecutionLog";
import { LibraryBrowser } from "../components/LibraryBrowser";

export function Session() {
  const { sessionId } = useParams<{ sessionId: string }>();
  useWebSocket(sessionId ?? null);

  const { phase, agents, dag, events, libraryResults, objective, isConnected } =
    useSessionStore();

  const agentList = Object.values(agents);
  const approvedCount = agentList.filter((a) => a.state === "APPROVED" || a.state === "COMPLETED").length;

  return (
    <div className="min-h-screen bg-gray-950 text-white font-mono">
      <PhaseIndicator phase={phase} />

      <div className="px-4 py-2 border-b border-gray-800 flex justify-between items-center text-xs">
        <span className="text-gray-300 truncate max-w-xl" title={objective}>
          {objective || "Loading..."}
        </span>
        <div className="flex items-center gap-4 shrink-0 ml-4">
          {agentList.length > 0 && (
            <span className="text-gray-400">
              {approvedCount}/{agentList.length} approved
            </span>
          )}
          <span className={isConnected ? "text-green-400" : "text-red-400"}>
            {isConnected ? "● LIVE" : "○ DISCONNECTED"}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 p-4 h-[calc(100vh-80px)]">
        {/* Left column: Agent Cards */}
        <div className="col-span-1 overflow-y-auto space-y-2">
          <div className="text-xs text-gray-500 mb-1 sticky top-0 bg-gray-950 py-1">
            AGENTS ({agentList.length})
          </div>
          {agentList.length === 0 && (
            <div className="text-gray-600 text-xs text-center py-12 border border-dashed border-gray-700 rounded-lg">
              Waiting for AgentMaster to design blueprint...
            </div>
          )}
          {agentList.map((a) => (
            <AgentCard key={a.agent_id} agent={a} />
          ))}
        </div>

        {/* Center column: DAG + Library */}
        <div className="col-span-1 space-y-4 overflow-y-auto">
          <div className="text-xs text-gray-500">DAG VISUALIZATION</div>
          {dag ? (
            <DAGVisualization dag={dag} agents={agents} />
          ) : (
            <div className="h-96 bg-gray-900 border border-dashed border-gray-700 rounded-lg flex items-center justify-center text-gray-600 text-xs">
              Agent graph will appear here once blueprint is ready...
            </div>
          )}
          {libraryResults.length > 0 && (
            <div>
              <div className="text-xs text-gray-500 mb-1">LIBRARY MATCHES</div>
              <LibraryBrowser patterns={libraryResults} />
            </div>
          )}
        </div>

        {/* Right column: Execution Log */}
        <div className="col-span-1 space-y-2">
          <div className="text-xs text-gray-500">EXECUTION LOG</div>
          <ExecutionLog events={events} />
          <div className="text-xs text-gray-600">
            Session: <span className="text-gray-400">{sessionId}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
