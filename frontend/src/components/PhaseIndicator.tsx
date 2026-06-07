import type { Phase } from "../types";

const PHASE_CONFIG: Record<Phase, { label: string; color: string; description: string }> = {
  DESIGN: {
    label: "DESIGN TIME",
    color: "bg-blue-700",
    description: "Building the agent graph",
  },
  DRYRUN: {
    label: "DRY RUN",
    color: "bg-yellow-600",
    description: "Validating in sandbox mode",
  },
  RUN: {
    label: "RUN TIME",
    color: "bg-green-700",
    description: "Executing against real systems",
  },
  COMPLETED: {
    label: "COMPLETED",
    color: "bg-gray-600",
    description: "All agents completed",
  },
};

export function PhaseIndicator({ phase }: { phase: Phase }) {
  const cfg = PHASE_CONFIG[phase];
  return (
    <div
      className={`${cfg.color} text-white px-6 py-2 flex items-center gap-3 font-mono text-sm`}
    >
      <span className="w-2 h-2 rounded-full bg-white inline-block animate-pulse" />
      <span className="font-bold tracking-widest">[{cfg.label}]</span>
      <span className="opacity-75 text-xs">{cfg.description}</span>
    </div>
  );
}
