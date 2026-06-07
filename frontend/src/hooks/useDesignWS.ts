import { useEffect, useRef, useCallback } from "react";
import { wsUrl } from "../api/client";
import { useDesignStore } from "../store/runStore";
import type { DesignWSEvent, AtomicAgent } from "../types";

export function useDesignWS(pipelineId: string | null, trigger: number = 0) {
  const wsRef = useRef<WebSocket | null>(null);

  const stop = useCallback(() => {
    wsRef.current?.close();
  }, []);

  useEffect(() => {
    if (!pipelineId) return;
    const s = useDesignStore.getState();
    s.reset();

    const socket = new WebSocket(wsUrl(`/ws/design/${pipelineId}`));
    wsRef.current = socket;

    socket.onopen = () => useDesignStore.getState().setConnected(true);
    socket.onclose = () => useDesignStore.getState().setConnected(false);
    socket.onerror = () => useDesignStore.getState().setConnected(false);

    socket.onmessage = (e: MessageEvent) => {
      const event = JSON.parse(e.data as string) as DesignWSEvent;
      const store = useDesignStore.getState();
      store.addEvent(event);

      switch (event.type) {
        case "PHASE_UPDATE":
          store.setPhase(event.phase);
          store.setPhaseMessage(event.message);
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
          store.setPhaseMessage("Design complete — all agents approved");
          break;
        default:
          break;
      }
    };

    return () => socket.close();
  }, [pipelineId, trigger]);

  return { stop };
}
