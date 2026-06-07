// frontend/src/components/CredentialsPanel.tsx
import { useState, useEffect } from "react";
import { api } from "../api/client";

interface Props {
  pipelineId: string;
  onClose: () => void;
}

interface KVRow {
  key: string;
  value: string;
  masked: boolean;
}

export function CredentialsPanel({ pipelineId, onClose }: Props) {
  const [rows, setRows] = useState<KVRow[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.get(`/api/pipelines/${pipelineId}`).then(({ data }) => {
      const inputs: Record<string, string> = data.default_inputs || {};
      setRows(
        Object.entries(inputs).map(([key, value]) => ({ key, value, masked: true }))
      );
    });
  }, [pipelineId]);

  const addRow = () => setRows((r) => [...r, { key: "", value: "", masked: false }]);
  const removeRow = (i: number) => setRows((r) => r.filter((_, idx) => idx !== i));
  const updateRow = (i: number, field: "key" | "value", val: string) =>
    setRows((r) => r.map((row, idx) => (idx === i ? { ...row, [field]: val } : row)));
  const toggleMask = (i: number) =>
    setRows((r) => r.map((row, idx) => (idx === i ? { ...row, masked: !row.masked } : row)));

  const handleSave = async () => {
    setSaving(true);
    const default_inputs: Record<string, string> = {};
    for (const row of rows) {
      if (row.key.trim()) default_inputs[row.key.trim()] = row.value;
    }
    try {
      await api.patch(`/api/pipelines/${pipelineId}/credentials`, { default_inputs });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      alert("Failed to save credentials.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-end">
      <div className="bg-[#0d1117] border-l border-gray-800 w-full max-w-md h-full flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800">
          <div>
            <h2 className="text-white font-bold font-mono text-sm">Pipeline Credentials</h2>
            <p className="text-gray-600 text-xs font-mono mt-0.5">
              Stored for scheduled &amp; webhook runs. Injected as env vars.
            </p>
          </div>
          <button className="text-gray-500 hover:text-white font-mono text-lg" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-2">
          {rows.map((row, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                className="flex-1 bg-gray-900 border border-gray-700 text-white text-xs px-3 py-2 rounded font-mono focus:outline-none focus:border-cyan-600"
                placeholder="KEY_NAME"
                value={row.key}
                onChange={(e) => updateRow(i, "key", e.target.value)}
              />
              <div className="relative flex-1">
                <input
                  className="w-full bg-gray-900 border border-gray-700 text-white text-xs px-3 py-2 rounded font-mono focus:outline-none focus:border-cyan-600 pr-8"
                  placeholder="value"
                  type={row.masked ? "password" : "text"}
                  value={row.value}
                  onChange={(e) => updateRow(i, "value", e.target.value)}
                />
                <button
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-600 hover:text-gray-300 text-xs"
                  onClick={() => toggleMask(i)}
                  title={row.masked ? "Show" : "Hide"}
                >
                  {row.masked ? "👁" : "🙈"}
                </button>
              </div>
              <button className="text-gray-600 hover:text-red-400 text-xs font-mono" onClick={() => removeRow(i)}>
                ✕
              </button>
            </div>
          ))}
          <button className="text-cyan-600 hover:text-cyan-400 text-xs font-mono mt-2" onClick={addRow}>
            + Add credential
          </button>
        </div>

        <div className="px-5 py-4 border-t border-gray-800 flex items-center justify-between">
          <p className="text-gray-700 text-xs font-mono">Values encrypted at rest via GCS</p>
          <button
            className="bg-cyan-700 hover:bg-cyan-600 disabled:bg-gray-700 disabled:text-gray-600 text-white font-bold px-5 py-2 rounded-lg text-sm font-mono transition-colors"
            onClick={handleSave}
            disabled={saving}
          >
            {saved ? "✓ Saved" : saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
