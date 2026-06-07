import { create } from "zustand";
import type { Run, AgentResult, DesignWSEvent, RunWSEvent, AtomicAgent, DAGData } from "../types";

// ── Design-time store ────────────────────────────────────────────────────────

interface DesignStore {
  isConnected: boolean;
  phase: string;
  phaseMessage: string;
  llmTokens: number;
  events: DesignWSEvent[];
  agents: Record<string, AtomicAgent>;
  dag: DAGData | null;
  isComplete: boolean;

  setConnected: (v: boolean) => void;
  setPhase: (p: string) => void;
  setPhaseMessage: (m: string) => void;
  setLlmTokens: (n: number) => void;
  addEvent: (e: DesignWSEvent) => void;
  upsertAgent: (a: AtomicAgent) => void;
  setAgentState: (id: string, state: AtomicAgent["state"]) => void;
  setDAG: (dag: DAGData) => void;
  setComplete: (v: boolean) => void;
  reset: () => void;
}

export const useDesignStore = create<DesignStore>((set) => ({
  isConnected: false,
  phase: "DESIGNING",
  phaseMessage: "",
  llmTokens: 0,
  events: [],
  agents: {},
  dag: null,
  isComplete: false,

  setConnected: (v) => set({ isConnected: v }),
  setPhase: (p) => set({ phase: p }),
  setPhaseMessage: (m) => set({ phaseMessage: m }),
  setLlmTokens: (n) => set({ llmTokens: n }),
  addEvent: (e) => set((s) => ({ events: [...s.events, e].slice(-500) })),
  upsertAgent: (a) =>
    set((s) => ({ agents: { ...s.agents, [a.agent_id]: a } })),
  setAgentState: (id, state) =>
    set((s) => ({
      agents: s.agents[id]
        ? { ...s.agents, [id]: { ...s.agents[id], state } }
        : s.agents,
    })),
  setDAG: (dag) => set({ dag }),
  setComplete: (v) => set({ isComplete: v }),
  reset: () =>
    set({ isConnected: false, phase: "DESIGNING", phaseMessage: "", llmTokens: 0, events: [], agents: {}, dag: null, isComplete: false }),
}));

// ── Run-time store ───────────────────────────────────────────────────────────

interface RunStore {
  run: Run | null;
  activeResults: Record<string, AgentResult>;
  runEvents: RunWSEvent[];
  isConnected: boolean;
  isComplete: boolean;

  setRun: (r: Run | null) => void;
  upsertResult: (r: AgentResult) => void;
  addRunEvent: (e: RunWSEvent) => void;
  setConnected: (v: boolean) => void;
  setComplete: (v: boolean) => void;
  reset: () => void;
}

export const useRunStore = create<RunStore>((set) => ({
  run: null,
  activeResults: {},
  runEvents: [],
  isConnected: false,
  isComplete: false,

  setRun: (r) => set({ run: r }),
  upsertResult: (r) =>
    set((s) => ({ activeResults: { ...s.activeResults, [r.agent_id]: r } })),
  addRunEvent: (e) => set((s) => ({ runEvents: [...s.runEvents, e].slice(-500) })),
  setConnected: (v) => set({ isConnected: v }),
  setComplete: (v) => set({ isComplete: v }),
  reset: () =>
    set({ run: null, activeResults: {}, runEvents: [], isConnected: false, isComplete: false }),
}));
