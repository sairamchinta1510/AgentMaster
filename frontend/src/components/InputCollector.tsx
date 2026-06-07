import { useState } from "react";

interface InputRequest {
  input_name: string;
  description: string;
  type: string;
  required: boolean;
}

interface Props {
  requests: InputRequest[];
  onSubmit: (values: Record<string, string>) => void;
}

export function InputCollector({ requests, onSubmit }: Props) {
  const [values, setValues] = useState<Record<string, string>>({});

  if (requests.length === 0) return null;

  return (
    <div className="bg-yellow-950 border border-yellow-700 rounded-lg p-4 font-mono">
      <div className="text-yellow-400 font-bold text-sm mb-3">[INPUT] INPUT REQUIRED</div>
      {requests.map((req) => (
        <div key={req.input_name} className="mb-3">
          <label className="block text-yellow-200 text-sm mb-1">
            {req.input_name}
            {req.required && <span className="text-red-400 ml-1">*</span>}
            <span className="text-gray-400 ml-2 text-xs">({req.type})</span>
          </label>
          <div className="text-gray-400 text-xs mb-1">{req.description}</div>
          <input
            type={req.type === "credential" ? "password" : "text"}
            className="w-full bg-gray-900 border border-gray-600 text-white px-3 py-1.5 rounded text-sm focus:outline-none focus:border-yellow-500"
            value={values[req.input_name] || ""}
            onChange={(e) =>
              setValues((v) => ({ ...v, [req.input_name]: e.target.value }))
            }
          />
        </div>
      ))}
      <button
        className="bg-yellow-600 hover:bg-yellow-500 text-black font-bold px-4 py-2 rounded text-sm transition-colors"
        onClick={() => onSubmit(values)}
      >
        Submit Inputs
      </button>
    </div>
  );
}
