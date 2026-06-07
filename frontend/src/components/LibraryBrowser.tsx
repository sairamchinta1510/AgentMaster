import type { LibraryPattern } from "../types";

export function LibraryBrowser({ patterns }: { patterns: LibraryPattern[] }) {
  if (patterns.length === 0) return null;

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 font-mono">
      <div className="text-cyan-400 font-bold text-xs mb-2">
        [LIBRARY] {patterns.length} matching pattern{patterns.length > 1 ? "s" : ""} found
      </div>
      <div className="space-y-1">
        {patterns.map((p, i) => (
          <div
            key={p.id}
            className="flex justify-between text-xs border-b border-gray-700 pb-1 last:border-0"
          >
            <span className="text-gray-300 truncate flex-1 mr-2">
              <span className="text-yellow-400 mr-1">#{i + 1}</span>
              {p.name}
            </span>
            <span className="text-gray-500 mr-2 shrink-0">{p.domain}</span>
            <span className="text-green-400 shrink-0">★ {p.quality_score}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
