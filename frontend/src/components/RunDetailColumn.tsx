// frontend/src/components/RunDetailColumn.tsx
import { useState } from "react";
import type { AgentResult, InputField } from "../types";

interface RunDetailColumnProps {
  agentId: string | null;
  agentName?: string;
  agentDescription?: string;
  result?: AgentResult;
  isRunning: boolean;
  userInputs: Record<string, string>;
  inputSchema: InputField[];
  onInputChange: (name: string, value: string) => void;
  onStartRun: () => void;
  starting: boolean;
  hasBlueprint: boolean;
}

export function RunDetailColumn({
  agentId,
  agentName,
  agentDescription,
  result,
  isRunning,
  userInputs,
  inputSchema,
  onInputChange,
  onStartRun,
  starting,
  hasBlueprint,
}: RunDetailColumnProps) {
  const [outputExpanded, setOutputExpanded] = useState(true);

  const showStartForm = !isRunning && !result;

  return (
    <div className="flex flex-col h-full font-mono overflow-y-auto">
      {/* Selected agent header */}
      {agentId && agentName && (
        <div className="shrink-0 mb-4">
          <div className="text-white font-bold text-sm">{agentName}</div>
          {agentDescription && (
            <div className="text-gray-500 text-xs mt-0.5">{agentDescription}</div>
          )}
          {isRunning && (
            <div className="mt-2 flex items-center gap-2">
              <span className="h-2 w-2 bg-purple-400 rounded-full animate-pulse" />
              <span className="text-purple-400 text-xs animate-pulse">Running…</span>
            </div>
          )}
        </div>
      )}

      {/* Input form + start button (shown when no active run) */}
      {showStartForm && (
        <div className="shrink-0">
          <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">
            {inputSchema.length > 0 ? "Your Inputs" : "No inputs required"}
          </div>
          {inputSchema.map((field) => (
            <div key={field.name} className="mb-3">
              <label className="text-xs text-gray-400 block mb-1">
                {field.name}
                {field.required && <span className="text-red-500 ml-1">*</span>}
                <span className="text-gray-600 ml-1">({field.type})</span>
              </label>
              <input
                type={field.type === "credential" ? "password" : "text"}
                className="w-full bg-gray-800 border border-gray-700 text-white px-3 py-2 rounded text-xs focus:outline-none focus:border-purple-500 transition-colors"
                placeholder={field.description}
                value={userInputs[field.name] || ""}
                onChange={(e) => onInputChange(field.name, e.target.value)}
                disabled={isRunning}
              />
            </div>
          ))}
          {hasBlueprint && (
            <button
              className="w-full mt-2 bg-purple-700 hover:bg-purple-600 text-white font-bold py-3 rounded-lg text-sm transition-colors disabled:opacity-50"
              onClick={onStartRun}
              disabled={starting || isRunning}
            >
              {starting ? "Starting…" : "▶ Start Run"}
            </button>
          )}
        </div>
      )}

      {/* Running spinner (agent selected but no result yet) */}
      {isRunning && !result && agentId && (
        <div className="flex-1 flex items-center justify-center min-h-[120px]">
          <div className="text-center text-purple-400">
            <div className="text-3xl mb-3 animate-spin">⟳</div>
            <div className="text-xs">Executing agent…</div>
          </div>
        </div>
      )}

      {/* Output panel */}
      {result && (
        <div className="flex-1 min-h-0">
          <button
            className="flex items-center justify-between w-full mb-2"
            onClick={() => setOutputExpanded((v) => !v)}
          >
            <div className="text-xs text-gray-500 uppercase tracking-wider">Output</div>
            <span className="text-gray-600 text-xs">{outputExpanded ? "▲" : "▼"}</span>
          </button>

          {result.error && (
            <div className="bg-red-950 border border-red-800 rounded-lg p-3 text-red-300 text-xs mb-3">
              ✗ {result.error}
            </div>
          )}

          {outputExpanded && Object.keys(result.output).length > 0 && (
            <pre className="text-xs text-gray-300 bg-gray-950 border border-gray-800 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap max-h-80">
              {JSON.stringify(result.output, null, 2)}
            </pre>
          )}

          {outputExpanded &&
            Object.keys(result.output).length === 0 &&
            !result.error && (
              <div className="text-gray-600 text-xs text-center py-4">
                No output data
              </div>
            )}

          {result.duration_ms != null && (
            <div className="text-gray-600 text-xs mt-2">
              Completed in {result.duration_ms}ms
            </div>
          )}
        </div>
      )}

      {/* Idle placeholder when no agent selected and no run */}
      {!agentId && showStartForm && inputSchema.length === 0 && !hasBlueprint && (
        <div className="flex-1 flex items-center justify-center text-gray-700 text-xs font-mono">
          Select an agent to see details
        </div>
      )}
    </div>
  );
}
