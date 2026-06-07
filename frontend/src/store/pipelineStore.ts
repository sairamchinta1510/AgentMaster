import { create } from "zustand";
import type { PipelineSummary, Pipeline } from "../types";

interface PipelineStore {
  pipelines: PipelineSummary[];
  activePipeline: Pipeline | null;

  setPipelines: (list: PipelineSummary[]) => void;
  upsertSummary: (summary: PipelineSummary) => void;
  removePipeline: (id: string) => void;
  setActivePipeline: (p: Pipeline | null) => void;
}

export const usePipelineStore = create<PipelineStore>((set) => ({
  pipelines: [],
  activePipeline: null,

  setPipelines: (list) => set({ pipelines: list }),
  upsertSummary: (summary) =>
    set((s) => {
      const exists = s.pipelines.find((p) => p.id === summary.id);
      if (exists) {
        return { pipelines: s.pipelines.map((p) => (p.id === summary.id ? summary : p)) };
      }
      return { pipelines: [summary, ...s.pipelines] };
    }),
  removePipeline: (id) =>
    set((s) => ({ pipelines: s.pipelines.filter((p) => p.id !== id) })),
  setActivePipeline: (p) => set({ activePipeline: p }),
}));
