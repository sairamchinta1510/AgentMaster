import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { createSession, listLibrary } from "../api/client";
import { LibraryBrowser } from "../components/LibraryBrowser";
import type { LibraryPattern } from "../types";

export function Home() {
  const [objective, setObjective] = useState("");
  const [loading, setLoading] = useState(false);
  const [library, setLibrary] = useState<LibraryPattern[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    listLibrary()
      .then((r) => setLibrary(r.data))
      .catch(() => {});
  }, []);

  const handleStart = async () => {
    if (!objective.trim()) return;
    setLoading(true);
    try {
      const { data } = await createSession(objective);
      navigate(`/session/${data.session_id}`);
    } finally {
      setLoading(false);
    }
  };

  const EXAMPLES = [
    "Analyze my GitHub repository for security vulnerabilities and generate a report",
    "Monitor application logs, identify errors, and create automated remediation scripts",
    "Audit financial transactions for compliance and flag suspicious activity",
  ];

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col items-center justify-center px-4 font-mono">
      <div className="w-full max-w-2xl">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-cyan-400 mb-2">AgentMaster</h1>
          <p className="text-gray-400 text-sm">
            Autonomous Agentic Graph Framework — describe any objective, watch AI agents execute it.
          </p>
        </div>

        <div className="bg-gray-900 border border-gray-700 rounded-lg p-6">
          <label className="block text-sm text-gray-300 mb-2">Your Objective</label>
          <textarea
            className="w-full bg-gray-800 border border-gray-600 text-white px-4 py-3 rounded-lg text-sm resize-none focus:outline-none focus:border-cyan-500 transition-colors"
            rows={4}
            placeholder="Describe any objective... e.g. 'Analyze my GitHub repo for security issues'"
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && e.ctrlKey) handleStart();
            }}
          />

          <div className="mt-2 flex gap-2 flex-wrap">
            {EXAMPLES.map((ex, i) => (
              <button
                key={i}
                className="text-xs text-gray-500 hover:text-cyan-400 underline"
                onClick={() => setObjective(ex)}
              >
                Example {i + 1}
              </button>
            ))}
          </div>

          <button
            className="mt-4 w-full bg-cyan-700 hover:bg-cyan-600 text-white font-bold py-3 rounded-lg text-sm transition-colors disabled:opacity-50"
            onClick={handleStart}
            disabled={loading || !objective.trim()}
          >
            {loading ? "Initializing..." : "→ Launch AgentMaster"}
          </button>
        </div>

        {library.length > 0 && (
          <div className="mt-6">
            <div className="text-xs text-gray-500 mb-2">RECENT AGENT LIBRARY</div>
            <LibraryBrowser patterns={library} />
          </div>
        )}
      </div>
    </div>
  );
}
