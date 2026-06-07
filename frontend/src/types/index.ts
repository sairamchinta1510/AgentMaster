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
