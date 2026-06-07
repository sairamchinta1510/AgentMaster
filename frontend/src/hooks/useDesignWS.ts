import { useEffect, useRef } from "react";
import { wsUrl } from "../api/client";
import { useDesignStore } from "../store/runStore";
import type { DesignWSEvent, AtomicAgent } from "../types";

export function useDesignWS(pipelineId: string | null) {
  const ws = useRef<WebSocket | null>(null);
  const store = useDesignStore();

  useEffect(() => {
    if (!pipelineId) return;
    store.reset();

    const socket = new WebSocket(wsUrl(`/ws/design/${pipelineId}`));
    ws.current = socket;

    socket.onopen = () => store.setConnected(true);
    socket.onclose = () => store.setConnected(false);
    socket.onerror = () => store.setConnected(false);

    socket.onmessage = (e: MessageEvent) => {
      const event = JSON.parse(e.data as string) as DesignWSEvent;
      store.addEvent(event);

      switch (event.type) {
        case "PHASE_UPDATE":
          store.setPhase(event.phase);
          break;

        case "DAG_BUILT":
          store.setDAG(event.dag);
          break;

        case "AGENT_PRODUCED":
          store.upsertAgent(event.spec as AtomicAgent);
          break;

        case "AGENT_STATE_CHANGE":
          store.setAgentState(event.agent_id, event.state);
          break;

        case "CRITIQUE_COMPLETE": {
          const existing = useDesignStore.getState().agents[event.agent_id];
          if (existing) {
            store.upsertAgent({
              ...existing,
              critique_iterations: event.iterations,
              quality_score: event.quality_score,
              critique_history: [...(existing.critique_history ?? []), event.critique],
            });
          }
          break;
        }

        case "DESIGN_COMPLETE":
          store.setComplete(true);
          break;

        default:
          break;
      }
    };

    return () => {
      socket.close();
    };
  }, [pipelineId]);

  return ws;
}
