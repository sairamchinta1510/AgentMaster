// frontend/src/components/RunDetailColumn.tsx
import { useState } from "react";
import type { AgentResult, InputField } from "../types";

interface RunDetailColumnProps {
  agentId: string | null;
  agentName?: string;
  agentDescription?: string;
  result?: AgentResult;
  isRunning: boolean;
  isComplete: boolean;
  allResults: Record<string, AgentResult>;
  userInputs: Record<string, string>;
  inputSchema: InputField[];
  onInputChange: (name: string, value: string) => void;
  onStartRun: () => void;
  starting: boolean;
  hasBlueprint: boolean;
}

function downloadMarkdown(content: string, filename: string) {
  const blob = new Blob([content], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function buildReport(allResults: Record<string, AgentResult>): string {
  const date = new Date().toISOString().slice(0, 10);
  const results = Object.values(allResults);
  const completed = results.filter((r) => r.status === "completed").length;
  const failed = results.filter((r) => r.status === "failed").length;

  const lines: string[] = [
    `# AgentMaster Run Report`,
    ``,
    `**Date:** ${date}  `,
    `**Agents:** ${results.length} total — ${completed} completed, ${failed} failed`,
    ``,
    `---`,
    ``,
  ];

  for (const r of results) {
    lines.push(`## ${r.agent_name}`);
    lines.push(``);
    lines.push(`**Status:** ${r.status}${r.duration_ms != null ? ` · ${r.duration_ms}ms` : ""}`);
    lines.push(``);
    if (r.error) {
      lines.push(`**Error:** ${r.error}`);
      lines.push(``);
    }
    if (Object.keys(r.output).length > 0) {
      for (const [k, v] of Object.entries(r.output)) {
        lines.push(`### ${k}`);
        lines.push(``);
        if (typeof v === "string") {
          lines.push(v);
        } else {
          lines.push("```json");
          lines.push(JSON.stringify(v, null, 2));
          lines.push("```");
        }
        lines.push(``);
      }
    }
    lines.push(`---`);
    lines.push(``);
  }

  return lines.join("\n");
}

function RunSummary({
  allResults,
  elapsed,
  onNewRun,
}: {
  allResults: Record<string, AgentResult>;
  elapsed: number;
  onNewRun: () => void;
}) {
  const results = Object.values(allResults);
  const completed = results.filter((r) => r.status === "completed");
  const failed = results.filter((r) => r.status === "failed");
  const totalMs = results.reduce((s, r) => s + (r.duration_ms ?? 0), 0);

  return (
    <div className="flex flex-col gap-4 h-full overflow-y-auto font-mono">
      {/* Summary card */}
      <div className={`rounded-xl border p-4 ${failed.length > 0 ? "bg-orange-950/30 border-orange-800" : "bg-green-950/30 border-green-800"}`}>
        <div className={`text-lg font-bold mb-1 ${failed.length > 0 ? "text-orange-300" : "text-green-300"}`}>
          {failed.length > 0 ? `⚠ Completed with ${failed.length} failure${failed.length > 1 ? "s" : ""}` : "✓ Run Complete"}
        </div>
        <div className="text-xs text-gray-400 flex gap-4">
          <span>✓ {completed.length} agents done</span>
          {failed.length > 0 && <span className="text-red-400">✗ {failed.length} failed</span>}
          {elapsed > 0 && <span>{elapsed}s total</span>}
          {totalMs > 0 && <span>~{Math.round(totalMs / 1000)}s agent time</span>}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          className="flex-1 bg-purple-700 hover:bg-purple-600 text-white text-xs font-bold py-2 rounded-lg transition-colors"
          onClick={onNewRun}
        >
          ▶ Run Again
        </button>
        <button
          className="flex-1 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-bold py-2 rounded-lg border border-gray-700 transition-colors"
          onClick={() => downloadMarkdown(buildReport(allResults), `agentmaster-report-${new Date().toISOString().slice(0, 10)}.md`)}
        >
          ⬇ Download Report
        </button>
      </div>

      {/* Per-agent summary */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">Agent Results</div>
        {results.map((r) => (
          <div
            key={r.agent_id}
            className={`rounded-lg border p-3 mb-2 text-xs ${
              r.status === "completed"
                ? "bg-green-950/20 border-green-900/50"
                : r.status === "failed"
                ? "bg-red-950/30 border-red-900/50"
                : "bg-gray-900 border-gray-800"
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className={`font-bold ${r.status === "completed" ? "text-green-300" : r.status === "failed" ? "text-red-300" : "text-gray-300"}`}>
                {r.status === "completed" ? "✓" : r.status === "failed" ? "✗" : "—"} {r.agent_name}
              </span>
              {r.duration_ms != null && (
                <span className="text-gray-600">{r.duration_ms}ms</span>
              )}
            </div>
            {r.error && <div className="text-red-400 mt-1">{r.error}</div>}
            {Object.keys(r.output).length > 0 && (
              <div className="text-gray-500 mt-1">
                {Object.keys(r.output).join(", ")}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export function RunDetailColumn({
  agentId,
  agentName,
  agentDescription,
  result,
  isRunning,
  isComplete,
  allResults,
  userInputs,
  inputSchema,
  onInputChange,
  onStartRun,
  starting,
  hasBlueprint,
}: RunDetailColumnProps) {
  const [outputExpanded, setOutputExpanded] = useState(true);
  const [elapsed] = useState(0);

  const showStartForm = !isRunning && !isComplete && !result;

  // After a run completes with no agent selected, show the summary
  if (isComplete && !agentId) {
    return (
      <RunSummary
        allResults={allResults}
        elapsed={elapsed}
        onNewRun={onStartRun}
      />
    );
  }

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

      {/* Input form + start button (shown when no active run and not complete) */}
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

          {isComplete && (
            <button
              className="mt-4 w-full bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-bold py-2 rounded-lg border border-gray-700 transition-colors"
              onClick={() =>
                downloadMarkdown(
                  buildReport(allResults),
                  `agentmaster-report-${new Date().toISOString().slice(0, 10)}.md`
                )
              }
            >
              ⬇ Download Full Report
            </button>
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

