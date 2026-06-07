// ── V2 types ────────────────────────────────────────────────────────────────

export interface InputField {
  name: string;
  type: "string" | "url" | "credential" | "file" | "selection";
  description: string;
  required: boolean;
}

export interface Pipeline {
  id: string;
  objective: string;
  name: string;
  input_schema: InputField[];
  blueprint: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
}

export interface PipelineSummary {
  id: string;
  objective: string;
  name: string;
  agent_count: number;
  created_at: string | null;
}

export interface AgentResult {
  agent_id: string;
  agent_name: string;
  status: "completed" | "failed" | "skipped";
  output: Record<string, unknown>;
  error: string | null;
  duration_ms: number | null;
}

export interface Run {
  id: string;
  pipeline_id: string;
  inputs: Record<string, string>;
  status: "pending" | "running" | "completed" | "failed";
  results: AgentResult[];
  created_at: string | null;
  completed_at: string | null;
}

export type DesignWSEvent =
  | { type: "DESIGN_STARTED"; pipeline_id: string; objective: string }
  | { type: "PHASE_UPDATE"; pipeline_id: string; phase: string; message: string }
  | { type: "BLUEPRINT_READY"; pipeline_id: string; blueprint: Record<string, unknown> }
  | { type: "DAG_BUILT"; pipeline_id: string; dag: DAGData }
  | { type: "AGENT_STARTED"; pipeline_id: string; agent_id: string; agent_name: string; state: AgentState }
  | { type: "AGENT_PRODUCED"; pipeline_id: string; agent_id: string; spec: AtomicAgent }
  | { type: "CRITIQUE_COMPLETE"; pipeline_id: string; agent_id: string; iterations: number; verdict: CritiqueVerdict; quality_score: number; critique: CritiqueResult }
  | { type: "AGENT_STATE_CHANGE"; pipeline_id: string; agent_id: string; state: AgentState }
  | { type: "DESIGN_COMPLETE"; pipeline_id: string; message: string; agent_count: number; approved_count: number; input_schema: InputField[] }
  | { type: "ERROR"; pipeline_id: string; message: string };

export type RunWSEvent =
  | { type: "RUN_STARTED"; run_id: string; pipeline_id: string; objective: string; inputs: Record<string, string> }
  | { type: "AGENT_STARTED"; run_id: string; agent_id: string; agent_name: string }
  | { type: "AGENT_RESULT"; run_id: string; agent_id: string; agent_name: string; status: string; output: Record<string, unknown>; error: string | null; duration_ms: number | null }
  | { type: "RUN_COMPLETE"; run_id: string; status: string; total_agents: number; completed: number; failed: number; results: AgentResult[] }
  | { type: "ERROR"; run_id: string; message: string };

// ── V1 types (kept for existing components) ─────────────────────────────────

export type Phase = "DESIGN" | "DRYRUN" | "RUN" | "COMPLETED";

export type AgentState =
  | "PENDING"
  | "LIBRARY_SEARCH"
  | "INPUT_COLLECTION"
  | "SPECIFYING"
  | "DESIGN_CRITIQUE_1"
  | "DESIGN_CRITIQUE_2"
  | "DESIGN_CRITIQUE_3"
  | "DESIGN_CRITIQUE_4"
  | "DESIGN_CRITIQUE_5"
  | "REVISING_SPEC"
  | "AUTO_FIX"
  | "RETHINK"
  | "APPROVED"
  | "USER_ESCALATED"
  | "SIMULATING"
  | "VALIDATED"
  | "EXECUTING"
  | "COMPLETED"
  | "FAILED_ESCALATED"
  | "SKIPPED";

export type CritiqueVerdict =
  | "APPROVED"
  | "NEEDS_REVISION"
  | "ESCALATE_AUTO_FIX"
  | "ESCALATE_RETHINK"
  | "ESCALATE_USER";

export interface CritiqueIssue {
  issue_id: string;
  severity: "critical" | "major" | "minor" | "informational";
  category: string;
  description: string;
  impact: string;
  recommendation: string;
  effort_estimate: "low" | "medium" | "high";
  auto_fixable: boolean;
}

export interface CritiqueResult {
  critique_id: string;
  target_agent: string;
  target_agent_name: string;
  phase: string;
  iteration: number;
  max_iterations: number;
  verdict: CritiqueVerdict;
  quality_score: number;
  errors_remaining: number;
  issues: CritiqueIssue[];
  approved_aspects: string[];
  remaining_errors: string[];
}

export interface AtomicAgent {
  agent_id: string;
  agent_name: string;
  description: string;
  state: AgentState;
  phase: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  critique_iterations: number;
  quality_score: number | null;
  critique_history: CritiqueResult[];
}

export interface DAGNode {
  node_id: string;
  agent_id: string;
  agent_name: string;
  depends_on: string[];
}

export interface DAGEdge {
  edge_id: string;
  from_node: string;
  to_node: string;
}

export interface DAGData {
  nodes: DAGNode[];
  edges: DAGEdge[];
}

export interface LibraryPattern {
  id: string;
  name: string;
  domain: string;
  quality_score: number;
  objective: string;
}

export interface WSEvent {
  type: string;
  session_id: string;
  [key: string]: unknown;
}
