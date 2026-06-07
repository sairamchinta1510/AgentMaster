import { create } from "zustand";
import type { Phase, AtomicAgent, DAGData, WSEvent, LibraryPattern } from "../types";

interface SessionStore {
  sessionId: string | null;
  objective: string;
  phase: Phase;
  agents: Record<string, AtomicAgent>;
  dag: DAGData | null;
  events: WSEvent[];
  libraryResults: LibraryPattern[];
  isConnected: boolean;

  setSession: (id: string, objective: string) => void;
  setPhase: (phase: Phase) => void;
  upsertAgent: (agent: AtomicAgent) => void;
  setAgentState: (agentId: string, state: AtomicAgent["state"]) => void;
  setDAG: (dag: DAGData) => void;
  addEvent: (event: WSEvent) => void;
  setLibraryResults: (results: LibraryPattern[]) => void;
  setConnected: (v: boolean) => void;
  reset: () => void;
}

export const useSessionStore = create<SessionStore>((set) => ({
  sessionId: null,
  objective: "",
  phase: "DESIGN",
  agents: {},
  dag: null,
  events: [],
  libraryResults: [],
  isConnected: false,

  setSession: (id, objective) => set({ sessionId: id, objective }),
  setPhase: (phase) => set({ phase }),
  upsertAgent: (agent) =>
    set((s) => ({ agents: { ...s.agents, [agent.agent_id]: agent } })),
  setAgentState: (agentId, state) =>
    set((s) => ({
      agents: s.agents[agentId]
        ? { ...s.agents, [agentId]: { ...s.agents[agentId], state } }
        : s.agents,
    })),
  setDAG: (dag) => set({ dag }),
  addEvent: (event) =>
    set((s) => ({ events: [event, ...s.events].slice(0, 500) })),
  setLibraryResults: (results) => set({ libraryResults: results }),
  setConnected: (v) => set({ isConnected: v }),
  reset: () =>
    set({
      sessionId: null,
      agents: {},
      dag: null,
      events: [],
      phase: "DESIGN",
      libraryResults: [],
    }),
}));
