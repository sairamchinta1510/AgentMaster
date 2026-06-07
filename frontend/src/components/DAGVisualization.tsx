import ReactFlow, {
  Controls,
  Background,
  MiniMap,
  type Node,
  type Edge,
} from "reactflow";
import "reactflow/dist/style.css";
import type { DAGData, AtomicAgent } from "../types";

const STATE_NODE_COLORS: Record<string, string> = {
  PENDING: "#374151",
  SPECIFYING: "#1d4ed8",
  DESIGN_CRITIQUE_1: "#b45309",
  DESIGN_CRITIQUE_2: "#b45309",
  DESIGN_CRITIQUE_3: "#b45309",
  DESIGN_CRITIQUE_4: "#c2410c",
  DESIGN_CRITIQUE_5: "#dc2626",
  REVISING_SPEC: "#1d4ed8",
  APPROVED: "#16a34a",
  COMPLETED: "#15803d",
  FAILED_ESCALATED: "#dc2626",
  USER_ESCALATED: "#7c3aed",
  SIMULATING: "#0891b2",
  VALIDATED: "#0d9488",
  EXECUTING: "#15803d",
};

interface Props {
  dag: DAGData;
  agents: Record<string, AtomicAgent>;
}

export function DAGVisualization({ dag, agents }: Props) {
  const agentByNodeId: Record<string, AtomicAgent> = {};
  for (const n of dag.nodes) {
    if (agents[n.agent_id]) {
      agentByNodeId[n.node_id] = agents[n.agent_id];
    }
  }

  const rfNodes: Node[] = dag.nodes.map((n, i) => {
    const agent = agentByNodeId[n.node_id];
    const state = agent?.state || "PENDING";
    return {
      id: n.node_id,
      position: { x: (i % 3) * 260, y: Math.floor(i / 3) * 130 },
      data: {
        label: (
          <div>
            <div className="font-bold text-xs">{n.agent_name}</div>
            <div className="text-xs opacity-70 mt-0.5">{state}</div>
          </div>
        ),
      },
      style: {
        background: STATE_NODE_COLORS[state] || "#374151",
        color: "white",
        border: "1px solid rgba(255,255,255,0.2)",
        borderRadius: 8,
        fontSize: 11,
        fontFamily: "monospace",
        padding: "8px 12px",
        minWidth: 140,
      },
    };
  });

  const rfEdges: Edge[] = dag.edges.map((e) => ({
    id: e.edge_id,
    source: e.from_node,
    target: e.to_node,
    style: { stroke: "#4b5563" },
    animated: true,
  }));

  return (
    <div className="w-full h-96 bg-gray-950 rounded-lg border border-gray-700 overflow-hidden">
      <ReactFlow nodes={rfNodes} edges={rfEdges} fitView>
        <Controls />
        <MiniMap
          nodeColor={(n) => (n.style?.background as string) || "#374151"}
          style={{ background: "#111827" }}
        />
        <Background color="#1f2937" gap={16} />
      </ReactFlow>
    </div>
  );
}
