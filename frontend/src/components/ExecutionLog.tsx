import { useRef, useEffect } from "react";
import type { WSEvent } from "../types";

const EVENT_COLORS: Record<string, string> = {
  SESSION_STARTED: "text-blue-400",
  PHASE_UPDATE: "text-cyan-400",
  LIBRARY_SEARCH: "text-gray-400",
  LIBRARY_RESULTS: "text-gray-500",
  BLUEPRINT_READY: "text-indigo-400",
  DAG_BUILT: "text-indigo-300",
  AGENT_STARTED: "text-yellow-300",
  AGENT_PRODUCED: "text-green-300",
  CRITIQUE_COMPLETE: "text-purple-300",
  AGENT_STATE_CHANGE: "text-orange-300",
  SESSION_COMPLETED: "text-green-500 font-bold",
  ERROR: "text-red-400 font-bold",
};

function summarize(event: WSEvent): string {
  switch (event.type) {
    case "PHASE_UPDATE":
      return `Phase: ${event.phase as string} — ${event.message as string}`;
    case "AGENT_STARTED":
      return `Agent started: ${event.agent_name as string}`;
    case "AGENT_PRODUCED":
      return `Agent produced: ${event.agent_id as string}`;
    case "CRITIQUE_COMPLETE":
      return `Critique: ${event.agent_id as string} → ${event.verdict as string} (${event.quality_score}/10)`;
    case "AGENT_STATE_CHANGE":
      return `${event.agent_id as string} → ${event.state as string}`;
    case "SESSION_COMPLETED":
      return `${event.message as string}`;
    case "ERROR":
      return `Error: ${event.message as string}`;
    case "LIBRARY_RESULTS":
      return `Library: ${(event.results as unknown[])?.length ?? 0} patterns found`;
    default:
      return (event.message as string) || event.type;
  }
}

export function ExecutionLog({ events }: { events: WSEvent[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  return (
    <div className="bg-gray-950 border border-gray-700 rounded-lg h-80 overflow-y-auto p-3 font-mono text-xs">
      {events.length === 0 && (
        <div className="text-gray-600 text-center py-8">
          Waiting for session events...
        </div>
      )}
      {[...events].reverse().map((e, i) => (
        <div key={i} className={`${EVENT_COLORS[e.type] || "text-gray-300"} mb-0.5`}>
          <span className="text-gray-600">[{e.type}]</span> {summarize(e)}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
