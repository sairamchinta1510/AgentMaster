import { useEffect, useRef } from "react";
import { wsUrl } from "../api/client";
import { useRunStore } from "../store/runStore";
import type { RunWSEvent, AgentResult } from "../types";

export function useRunWS(runId: string | null) {
  const ws = useRef<WebSocket | null>(null);
  const store = useRunStore();

  useEffect(() => {
    if (!runId) return;
    store.reset();

    const socket = new WebSocket(wsUrl(`/ws/run/${runId}`));
    ws.current = socket;

    socket.onopen = () => store.setConnected(true);
    socket.onclose = () => store.setConnected(false);
    socket.onerror = () => store.setConnected(false);

    socket.onmessage = (e: MessageEvent) => {
      const event = JSON.parse(e.data as string) as RunWSEvent;
      store.addRunEvent(event);

      switch (event.type) {
        case "AGENT_RESULT":
          store.upsertResult({
            agent_id: event.agent_id,
            agent_name: event.agent_name,
            status: event.status as AgentResult["status"],
            output: event.output,
            error: event.error,
            duration_ms: event.duration_ms,
          });
          break;

        case "RUN_COMPLETE":
          store.setComplete(true);
          for (const r of event.results) {
            store.upsertResult(r);
          }
          break;

        default:
          break;
      }
    };

    return () => {
      socket.close();
    };
  }, [runId]);

  return ws;
}
