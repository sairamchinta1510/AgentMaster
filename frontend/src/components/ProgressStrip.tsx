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
  narrationHighlight?: string; // e.g. agent name shown in color
  narrationSub?: string;
  pills: StepPill[];
  progress: number;
  total: number;
  done: number;
  mode: "design" | "run" | "idle";
}

const STATE_PILL: Record<StepPill["state"], string> = {
  done:           "bg-green-900/60 text-green-300 border-green-700",
  "active-design":"bg-amber-900/60 text-amber-200 border-amber-500 animate-pulse",
  "active-run":   "bg-purple-900/60 text-purple-200 border-purple-500 animate-pulse",
  pending:        "bg-gray-900/40 text-gray-600 border-gray-800",
  error:          "bg-red-900/60 text-red-300 border-red-600",
};

const STATE_DOT: Record<StepPill["state"], string> = {
  done:           "bg-green-400",
  "active-design":"bg-amber-400 animate-pulse",
  "active-run":   "bg-purple-400 animate-pulse",
  pending:        "bg-gray-700",
  error:          "bg-red-400",
};

export function ProgressStrip({
  narration,
  narrationHighlight,
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

  const stripBg   = mode === "design" ? "bg-[#071828]" : mode === "run" ? "bg-[#110a24]" : "bg-gray-950";
  const stripBorder = mode === "design" ? "border-l-4 border-l-cyan-600 border-b border-b-cyan-900" :
                      mode === "run"    ? "border-l-4 border-l-purple-600 border-b border-b-purple-900" :
                                          "border-b border-gray-800";
  const barColor  = mode === "design" ? "bg-gradient-to-r from-cyan-500 to-amber-500" :
                    mode === "run"    ? "bg-purple-500" : "bg-gray-700";
  const dotColor  = mode === "design" ? "bg-amber-400 animate-pulse" :
                    mode === "run"    ? "bg-purple-400 animate-pulse" : "bg-gray-600";
  const countColor = mode === "design" ? "text-amber-400" : mode === "run" ? "text-purple-300" : "text-gray-600";

  return (
    <div className={`shrink-0 px-4 py-3 ${stripBg} ${stripBorder}`}>
      {/* Narration */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-start gap-2 min-w-0">
          <span className={`mt-1 h-2.5 w-2.5 rounded-full shrink-0 ${dotColor}`} />
          <div className="min-w-0">
            <div className="text-sm font-semibold text-white leading-tight">
              {narration}
              {narrationHighlight && (
                <span className="text-amber-400 mx-1">{narrationHighlight}</span>
              )}
            </div>
            {narrationSub && (
              <div className="text-gray-500 text-xs mt-0.5">{narrationSub}</div>
            )}
          </div>
        </div>
        {total > 0 && (
          <div className={`text-sm font-bold shrink-0 ${countColor}`}>
            {done} / {total} {mode === "design" ? "approved" : mode === "run" ? "done" : ""}
          </div>
        )}
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-gray-800 rounded-full mb-2.5">
        <div
          className={`h-1.5 rounded-full transition-all duration-700 ${barColor}`}
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Step pills */}
      {pills.length > 0 && (
        <div ref={pillsRef} className="flex gap-1.5 overflow-x-auto pb-0.5">
          {pills.map((p, i) => (
            <div
              key={p.id}
              data-active={p.state === "active-design" || p.state === "active-run" ? "true" : undefined}
              className={`flex items-center gap-1.5 border rounded-full px-3 py-1 text-xs whitespace-nowrap shrink-0 font-mono ${STATE_PILL[p.state]}`}
            >
              <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${STATE_DOT[p.state]}`} />
              {i + 1}. {p.label}
              {p.detail && <span className="opacity-70">{p.detail}</span>}
              {p.state === "done" && <span className="text-green-400">✓</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
