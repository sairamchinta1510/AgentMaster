// frontend/src/components/ProgressStrip.tsx
import { useEffect, useRef } from "react";

export interface StepPill {
  id: string;
  label: string;
  state: "done" | "active-design" | "active-run" | "pending" | "error";
  detail?: string;
}

interface ProgressStripProps {
  narration: string;
  narrationSub?: string;
  pills: StepPill[];
  progress: number;
  total: number;
  done: number;
  mode: "design" | "run" | "idle";
}

const STATE_PILL: Record<StepPill["state"], string> = {
  done:           "bg-green-700 text-green-200 border-green-500",
  "active-design":"bg-amber-700 text-amber-100 border-amber-400 animate-pulse",
  "active-run":   "bg-purple-700 text-purple-100 border-purple-400 animate-pulse",
  pending:        "bg-gray-800 text-gray-500 border-gray-700",
  error:          "bg-red-800 text-red-200 border-red-500",
};

const STATE_DOT: Record<StepPill["state"], string> = {
  done:           "bg-green-400",
  "active-design":"bg-amber-400 animate-pulse",
  "active-run":   "bg-purple-400 animate-pulse",
  pending:        "bg-gray-600",
  error:          "bg-red-400",
};

export function ProgressStrip({
  narration,
  narrationSub,
  pills,
  progress,
  total,
  done,
  mode,
}: ProgressStripProps) {
  const pillsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!pillsRef.current) return;
    const active = pillsRef.current.querySelector<HTMLElement>("[data-active='true']");
    if (active) active.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  }, [pills]);

  const barColor =
    mode === "design" ? "bg-gradient-to-r from-cyan-600 to-amber-500" :
    mode === "run"    ? "bg-purple-600" :
                        "bg-gray-700";

  const dotColor =
    mode === "idle"   ? "bg-gray-600" :
    mode === "design" ? "bg-cyan-400 animate-pulse" :
                        "bg-purple-400 animate-pulse";

  const borderColor =
    mode === "design" ? "border-cyan-900" :
    mode === "run"    ? "border-purple-900" :
                        "border-gray-800";

  return (
    <div className={`shrink-0 border-b ${borderColor} bg-gray-950 px-4 py-2`}>
      {/* Narration row */}
      <div className="flex items-start gap-2 mb-2">
        <span className={`mt-1 h-2 w-2 rounded-full shrink-0 ${dotColor}`} />
        <div className="flex-1 min-w-0">
          <div className="text-white text-xs font-semibold truncate">{narration}</div>
          {narrationSub && (
            <div className="text-gray-500 text-xs truncate mt-0.5">{narrationSub}</div>
          )}
        </div>
        {total > 0 && (
          <div className="text-gray-500 text-xs shrink-0 ml-2">
            {done} / {total} {mode === "design" ? "approved" : mode === "run" ? "done" : ""}
          </div>
        )}
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-gray-800 rounded-full mb-2">
        <div
          className={`h-1 rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Step pills */}
      {pills.length > 0 && (
        <div ref={pillsRef} className="flex gap-1.5 overflow-x-auto pb-0.5">
          {pills.map((p, i) => (
            <div
              key={p.id}
              data-active={
                p.state === "active-design" || p.state === "active-run" ? "true" : undefined
              }
              className={`flex items-center gap-1 border rounded px-2 py-0.5 text-xs whitespace-nowrap shrink-0 ${STATE_PILL[p.state]}`}
            >
              <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${STATE_DOT[p.state]}`} />
              <span>
                {i + 1}. {p.label}
              </span>
              {p.detail && <span className="opacity-60 text-xs">{p.detail}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
