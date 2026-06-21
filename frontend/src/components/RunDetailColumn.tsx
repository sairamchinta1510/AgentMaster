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
    if (r.error) { lines.push(`**Error:** ${r.error}`); lines.push(``); }
    for (const [k, v] of Object.entries(r.output)) {
      lines.push(`### ${k}`);
      lines.push(``);
      lines.push(typeof v === "string" ? v : "```json\n" + JSON.stringify(v, null, 2) + "\n```");
      lines.push(``);
    }
    lines.push(`---`); lines.push(``);
  }
  return lines.join("\n");
}

// ── Rich output value renderer ────────────────────────────────────────────────

function isPath(s: string) { return /^(\/|[A-Z]:\\|\.\/|~\/)/.test(s) || s.includes("/log") || s.includes("\\log"); }
function isUrl(s: string) { return /^https?:\/\//.test(s); }
function isHtml(s: string) { return /^\s*<!doctype html|^\s*<html/i.test(s.trim()); }
function humanize(key: string) { return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()); }

function downloadHtml(content: string, filename: string) {
  const blob = new Blob([content], { type: "text/html" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function RichValue({ label, value }: { label: string; value: unknown }) {
  const [expanded, setExpanded] = useState(true);

  if (value === null || value === undefined) return null;

  // Array of strings / paths
  if (Array.isArray(value)) {
    return (
      <div className="mb-4">
        <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">{humanize(label)}</div>
        <div className="space-y-1">
          {(value as unknown[]).map((item, i) => (
            <div key={i} className="flex items-start gap-2 text-sm">
              <span className="text-purple-400 mt-0.5 shrink-0">▸</span>
              {typeof item === "string" && isPath(item) ? (
                <code className="text-amber-300 bg-amber-900/20 px-2 py-0.5 rounded font-mono text-xs break-all">{item}</code>
              ) : typeof item === "string" ? (
                <span className="text-gray-200">{item}</span>
              ) : (
                <code className="text-gray-300 text-xs">{JSON.stringify(item)}</code>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Nested object
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>);
    return (
      <div className="mb-4">
        <button onClick={() => setExpanded((v) => !v)} className="flex items-center gap-2 text-xs text-gray-500 uppercase tracking-wider mb-2 w-full text-left">
          {humanize(label)} <span className="text-gray-700">{expanded ? "▲" : "▼"}</span>
        </button>
        {expanded && (
          <div className="bg-gray-900/60 border border-gray-800 rounded-lg p-3 space-y-2">
            {entries.map(([k, v]) => (
              <div key={k} className="flex flex-col gap-0.5">
                <span className="text-xs text-gray-500">{humanize(k)}</span>
                <span className="text-gray-200 text-sm break-words">
                  {typeof v === "string" ? v : JSON.stringify(v)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // URL
  if (typeof value === "string" && isUrl(value)) {
    return (
      <div className="mb-4">
        <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">{humanize(label)}</div>
        <a href={value} target="_blank" rel="noreferrer" className="text-cyan-400 hover:text-cyan-300 text-sm underline break-all">{value}</a>
      </div>
    );
  }

  // File path
  if (typeof value === "string" && isPath(value)) {
    return (
      <div className="mb-4">
        <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">{humanize(label)}</div>
        <code className="text-amber-300 bg-amber-900/20 border border-amber-900/40 px-3 py-1.5 rounded font-mono text-sm block break-all">{value}</code>
      </div>
    );
  }

  // HTML content — render in iframe with download option
  if (typeof value === "string" && isHtml(value)) {
    const [showPreview, setShowPreview] = useState(true);
    return (
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <div className="text-xs text-gray-500 uppercase tracking-wider">{humanize(label)}</div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowPreview(!showPreview)}
              className="text-xs bg-blue-900/40 hover:bg-blue-800/60 text-blue-300 px-3 py-1 rounded border border-blue-700/50 transition-colors"
            >
              {showPreview ? "Hide Preview" : "Show Preview"}
            </button>
            <button
              onClick={() => downloadHtml(value, `output-${Date.now()}.html`)}
              className="text-xs bg-purple-900/40 hover:bg-purple-800/60 text-purple-300 px-3 py-1 rounded border border-purple-700/50 transition-colors"
            >
              ⬇ Download HTML
            </button>
          </div>
        </div>
        {showPreview && (
          <iframe
            srcDoc={value}
            className="w-full h-[600px] bg-white rounded-lg border-2 border-gray-700"
            sandbox="allow-same-origin"
            title={`HTML Preview: ${label}`}
          />
        )}
        {!showPreview && (
          <div className="text-gray-400 text-xs italic bg-gray-900/40 border border-gray-800 rounded-lg p-3">
            HTML preview hidden. Click "Show Preview" to display or "Download HTML" to save.
          </div>
        )}
      </div>
    );
  }

  // Long string — render as readable text
  if (typeof value === "string" && value.length > 80) {
    return (
      <div className="mb-4">
        <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">{humanize(label)}</div>
        <div className="text-gray-200 text-sm leading-relaxed whitespace-pre-wrap bg-gray-900/40 border border-gray-800 rounded-lg p-3">
          {value}
        </div>
      </div>
    );
  }

  // Short string / number / bool — inline chip
  return (
    <div className="mb-3 flex items-center gap-3">
      <span className="text-xs text-gray-500 uppercase tracking-wider shrink-0">{humanize(label)}</span>
      <span className={`text-sm font-mono px-2 py-0.5 rounded ${
        value === true ? "bg-green-900/40 text-green-300" :
        value === false ? "bg-red-900/40 text-red-300" :
        typeof value === "number" ? "bg-purple-900/40 text-purple-300" :
        "text-gray-200"
      }`}>{String(value)}</span>
    </div>
  );
}

// ── Run Summary ───────────────────────────────────────────────────────────────

function RunSummary({ allResults, elapsed, onNewRun }: {
  allResults: Record<string, AgentResult>;
  elapsed: number;
  onNewRun: () => void;
}) {
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const results = Object.values(allResults);
  const completed = results.filter((r) => r.status === "completed");
  const failed = results.filter((r) => r.status === "failed");
  const totalMs = results.reduce((s, r) => s + (r.duration_ms ?? 0), 0);

  return (
    <div className="flex flex-col gap-4 h-full overflow-y-auto font-mono">
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

      <div className="flex gap-2">
        <button className="flex-1 bg-purple-700 hover:bg-purple-600 text-white text-xs font-bold py-2 rounded-lg transition-colors" onClick={onNewRun}>▶ Run Again</button>
        <button className="flex-1 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-bold py-2 rounded-lg border border-gray-700 transition-colors"
          onClick={() => downloadMarkdown(buildReport(allResults), `agentmaster-report-${new Date().toISOString().slice(0, 10)}.md`)}>
          ⬇ Download Report
        </button>
      </div>

      {/* Expandable per-agent results */}
      <div className="flex-1 min-h-0 overflow-y-auto space-y-2">
        <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Results by Agent</div>
        {results.map((r) => (
          <div key={r.agent_id} className={`rounded-lg border ${r.status === "completed" ? "border-green-900/50" : r.status === "failed" ? "border-red-900/50" : "border-gray-800"}`}>
            <button className="w-full flex items-center justify-between p-3 text-left" onClick={() => setExpandedAgent(expandedAgent === r.agent_id ? null : r.agent_id)}>
              <div className="flex items-center gap-2">
                <span className={r.status === "completed" ? "text-green-400" : r.status === "failed" ? "text-red-400" : "text-gray-500"}>
                  {r.status === "completed" ? "✓" : r.status === "failed" ? "✗" : "—"}
                </span>
                <span className="text-white text-xs font-bold">{r.agent_name}</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-600">
                {r.duration_ms != null && <span>{r.duration_ms}ms</span>}
                <span>{expandedAgent === r.agent_id ? "▲" : "▼"}</span>
              </div>
            </button>
            {expandedAgent === r.agent_id && (
              <div className="px-3 pb-3 border-t border-gray-800/60 pt-3">
                {r.error && <div className="text-red-400 text-xs mb-2">✗ {r.error}</div>}
                {Object.entries(r.output).map(([k, v]) => (
                  <RichValue key={k} label={k} value={v} />
                ))}
                {Object.keys(r.output).length === 0 && !r.error && (
                  <div className="text-gray-600 text-xs">No output</div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function RunDetailColumn({
  agentId, agentName, agentDescription, result, isRunning, isComplete,
  allResults, userInputs, inputSchema, onInputChange, onStartRun, starting, hasBlueprint,
}: RunDetailColumnProps) {
  const [elapsed] = useState(0);

  const showStartForm = !isRunning && !isComplete && !result;

  if (isComplete && !agentId) {
    return <RunSummary allResults={allResults} elapsed={elapsed} onNewRun={onStartRun} />;
  }

  return (
    <div className="flex flex-col h-full font-mono overflow-y-auto">
      {/* Agent header */}
      {agentId && agentName && (
        <div className="shrink-0 mb-4">
          <div className="text-white font-bold text-sm">{agentName}</div>
          {agentDescription && <div className="text-gray-500 text-xs mt-0.5">{agentDescription}</div>}
          {isRunning && (
            <div className="mt-2 flex items-center gap-2">
              <span className="h-2 w-2 bg-purple-400 rounded-full animate-pulse" />
              <span className="text-purple-400 text-xs animate-pulse">Running…</span>
            </div>
          )}
        </div>
      )}

      {/* Input form */}
      {showStartForm && (
        <div className="shrink-0">
          <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">
            {inputSchema.length > 0 ? "Your Inputs" : "No inputs required"}
          </div>
          {inputSchema.map((field) => (
            <div key={field.name} className="mb-3">
              <label className="text-xs text-gray-400 block mb-1">
                {field.name}{field.required && <span className="text-red-500 ml-1">*</span>}
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

      {/* Running spinner */}
      {isRunning && !result && agentId && (
        <div className="flex-1 flex items-center justify-center min-h-[120px]">
          <div className="text-center text-purple-400">
            <div className="text-3xl mb-3 animate-spin">⟳</div>
            <div className="text-xs">Executing agent…</div>
          </div>
        </div>
      )}

      {/* Rich output panel */}
      {result && (
        <div className="flex-1 min-h-0 overflow-y-auto">
          <div className="text-xs text-gray-500 uppercase tracking-wider mb-3">Output</div>

          {result.error && (
            <div className="bg-red-950 border border-red-800 rounded-lg p-3 text-red-300 text-xs mb-3">✗ {result.error}</div>
          )}

          {Object.entries(result.output).map(([k, v]) => (
            <RichValue key={k} label={k} value={v} />
          ))}

          {Object.keys(result.output).length === 0 && !result.error && (
            <div className="text-gray-600 text-xs text-center py-4">No output data</div>
          )}

          {result.duration_ms != null && (
            <div className="text-gray-600 text-xs mt-2 border-t border-gray-800 pt-2">
              Completed in {result.duration_ms}ms
            </div>
          )}

          {isComplete && (
            <button
              className="mt-4 w-full bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-bold py-2 rounded-lg border border-gray-700 transition-colors"
              onClick={() => downloadMarkdown(buildReport(allResults), `agentmaster-report-${new Date().toISOString().slice(0, 10)}.md`)}
            >
              ⬇ Download Full Report
            </button>
          )}
        </div>
      )}

      {!agentId && showStartForm && inputSchema.length === 0 && !hasBlueprint && (
        <div className="flex-1 flex items-center justify-center text-gray-700 text-xs font-mono">
          Select an agent to see details
        </div>
      )}
    </div>
  );
}
