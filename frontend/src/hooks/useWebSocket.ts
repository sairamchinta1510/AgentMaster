import { useEffect, useRef } from "react";
import { useSessionStore } from "../store/sessionStore";
import type { WSEvent, AtomicAgent } from "../types";

const WS_BASE = import.meta.env.VITE_WS_URL || "ws://localhost:8001";

export function useWebSocket(sessionId: string | null) {
  const ws = useRef<WebSocket | null>(null);
  const store = useSessionStore();

  useEffect(() => {
    if (!sessionId) return;

    const socket = new WebSocket(`${WS_BASE}/ws/${sessionId}`);
    ws.current = socket;

    socket.onopen = () => store.setConnected(true);
    socket.onclose = () => store.setConnected(false);
    socket.onerror = () => store.setConnected(false);

    socket.onmessage = (e: MessageEvent) => {
      const event: WSEvent = JSON.parse(e.data as string);
      store.addEvent(event);

      switch (event.type) {
        case "PHASE_UPDATE":
          store.setPhase(event.phase as "DESIGN" | "DRYRUN" | "RUN");
          break;

        case "AGENT_PRODUCED":
          if (event.spec) {
            store.upsertAgent(event.spec as AtomicAgent);
          }
          break;

        case "AGENT_STATE_CHANGE":
          store.setAgentState(
            event.agent_id as string,
            event.state as AtomicAgent["state"]
          );
          break;

        case "DAG_BUILT":
          if (event.dag) {
            store.setDAG(
              event.dag as Parameters<typeof store.setDAG>[0]
            );
          }
          break;

        case "LIBRARY_RESULTS":
          store.setLibraryResults(
            (event.results as Parameters<typeof store.setLibraryResults>[0]) || []
          );
          break;

        case "CRITIQUE_COMPLETE": {
          const agentId = event.agent_id as string;
          const existing = useSessionStore.getState().agents[agentId];
          if (existing && event.critique) {
            store.upsertAgent({
              ...existing,
              critique_iterations: event.iterations as number,
              quality_score: event.quality_score as number,
              critique_history: [
                ...existing.critique_history,
                event.critique as AtomicAgent["critique_history"][0],
              ],
            });
          }
          break;
        }

        default:
          break;
      }
    };

    return () => {
      socket.close();
    };
  }, [sessionId]);

  return ws;
}
