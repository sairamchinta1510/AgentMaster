import { useEffect, useRef, useCallback } from "react";
import { wsUrl } from "../api/client";
import { useDesignStore } from "../store/runStore";
import type { AtomicAgent } from "../types";

interface ExtendPayload {
  new_agents: Array<{ agent_id: string; agent_name: string; [k: string]: unknown }>;
  new_edges: Array<{ from: string; to: string; payload_description?: string }>;
}

export function useExtendWS(
  pipelineId: string | null,
  trigger: number,
  payload: ExtendPayload | null,
  onComplete: (blueprint: Record<string, unknown>) => void,
) {
  const wsRef = useRef<WebSocket | null>(null);

  const stop = useCallback(() => {
    wsRef.current?.close();
  }, []);

  useEffect(() => {
    if (!pipelineId || trigger < 0 || !payload) return;

    const store = useDesignStore.getState();
    // Don't reset — we want to keep existing agents visible, just add new ones
    store.setConnected(true);
    store.setPhaseMessage("Connecting to extend pipeline…");

    const socket = new WebSocket(wsUrl(`/ws/extend/${pipelineId}`));
    wsRef.current = socket;

    socket.onopen = () => {
      useDesignStore.getState().setConnected(true);
    };
    socket.onclose = () => useDesignStore.getState().setConnected(false);
    socket.onerror = () => useDesignStore.getState().setConnected(false);

    socket.onmessage = (e: MessageEvent) => {
      const event = JSON.parse(e.data as string) as { type: string; [k: string]: unknown };
      const s = useDesignStore.getState();

      switch (event.type) {
        case "EXTEND_READY":
          // Server is ready — send the selected agents
          socket.send(JSON.stringify(payload));
          break;

        case "PHASE_UPDATE":
          s.setPhase(event.phase as string);
          s.setPhaseMessage(event.message as string);
          s.setLlmTokens(0);
          break;

        case "LLM_STREAM":
          s.setLlmTokens(event.tokens as number);
          break;

        case "AGENT_STARTED":
          // Add new agent as SPECIFYING so it shows up in the list immediately
          s.upsertAgent({
            agent_id: event.agent_id as string,
            agent_name: event.agent_name as string,
            phase: "design_time",
            state: "SPECIFYING" as const,
            description: "",
            input_schema: {},
            output_schema: {},
            critique_iterations: 0,
            quality_score: null,
            critique_history: [],
          });
          break;

        case "AGENT_PRODUCED":
          s.upsertAgent(event.spec as AtomicAgent);
          break;

        case "AGENT_STATE_CHANGE":
          s.setAgentState(event.agent_id as string, event.state as AtomicAgent["state"]);
          break;

        case "CRITIQUE_COMPLETE": {
          const existing = useDesignStore.getState().agents[event.agent_id as string];
          if (existing) {
            s.upsertAgent({
              ...existing,
              critique_iterations: event.iterations as number,
              quality_score: event.quality_score as number,
              critique_history: [...(existing.critique_history ?? []), event.critique as never],
            });
          }
          break;
        }

        case "EXTEND_COMPLETE":
          s.setComplete(true);
          s.setPhaseMessage(`Extension complete — pipeline now has ${event.total_agent_count} agents`);
          onComplete(event.blueprint as Record<string, unknown>);
          socket.close();
          break;

        case "ERROR":
          s.setPhaseMessage(`Error: ${event.message as string}`);
          socket.close();
          break;
      }
    };

    return () => socket.close();
  }, [pipelineId, trigger]);  // eslint-disable-line react-hooks/exhaustive-deps

  return { stop };
}
