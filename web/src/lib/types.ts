export type Verdict = "ALLOW" | "APPROVAL" | "BLOCK";
export type AgentStatus =
  | "IDLE"
  | "OBSERVING"
  | "PLANNING"
  | "PROPOSING"
  | "WAITING_FOR_AUTHORIZATION"
  | "WAITING_FOR_APPROVAL"
  | "EXECUTING"
  | "COMPLETED"
  | "BLOCKED"
  | "FAILED"
  | "STOPPED"
  | "PAUSED";
export type BrowserStatus = "DISCONNECTED" | "STARTING" | "READY" | "NAVIGATING" | "LOADED" | "STOPPED" | "ERROR";

export interface SecurityDecision {
  verdict: Verdict;
  policy_ids: string[];
  reasons: string[];
  risk: string;
  fail_closed: boolean;
  evaluated_at: number;
}

export interface BrowserMeta {
  status: BrowserStatus;
  url: string;
  host: string;
  title: string;
  page_trust: string;
  page_class: string;
}

export interface AgentMeta {
  status: AgentStatus;
  task: string;
  planner: string;
  error: { title: string; detail: string; suggested?: string[] } | null;
}

export interface ProvenanceNode {
  node_id: string;
  kind: string;
  label: string;
  detail: string | null;
  data_class: string | null;
  trust: string | null;
  origin: string | null;
  ts: number;
  action_id: string | null;
}

export interface Chain {
  chain_id: string;
  action_id: string;
  nodes: ProvenanceNode[];
}

export interface PendingApproval {
  action_id: string;
  exchange: string;
  expires_in: number;
  proposal: unknown;
  decision: { verdict: Verdict; policy_ids: string[]; reasons: string[]; risk: string };
  provenance: unknown[];
}

export interface Threat {
  type: string;
  title: string;
  detail: string;
  severity: string;
  story: {
    what_page_tried?: string;
    what_agent_proposed?: string;
    data_involved?: { ph: string; class: string }[];
    where_going?: string;
    policy_stopped?: string[];
    what_happened?: string;
    induced?: boolean;
  };
  action_id?: string;
}

export interface Snapshot {
  session_id: string;
  generation: number;
  created: number;
  browser: BrowserMeta;
  agent: AgentMeta;
  human_control: boolean;
  narrative: string;
  current_action: Record<string, unknown> | null;
  security: SecurityDecision | null;
  pending_approval: PendingApproval | null;
  provenance: Chain | null;
  data: { entries: { ph: string; data_class: string; source: string; hint?: string }[]; canary: string | null };
  threats: Threat[];
  audit_count: number;
  event_count: number;
  executed_count: number;
  proposal_count: number;
}

export interface SentinelEvent {
  seq: number;
  type: string;
  ref: string | null;
  message: string | null;
  data: Record<string, unknown>;
  generation: number;
  created: number;
}

export interface AuditRecord {
  id: number;
  session_id?: string;
  event_type: string;
  ref?: string;
  created: number;
  data?: unknown;
}

export interface JudgeRun {
  session_id: string;
  scenario: string;
  state: Snapshot;
}

export interface BenchmarkSummary {
  run_id: number;
  created: number;
  elapsed_seconds: number;
  total_cases: number;
  scenarios: Record<string, { count: number; allows?: number; completed?: number; blocked?: number; prevented?: number; approvals?: number; approved_executions?: number }>;
  metrics: Record<string, number>;
  cases: {
    scenario: string;
    terminal: string;
    allows: number;
    blocked: boolean;
    prevented: boolean;
    approvals: number;
    executed: number;
    threats: number;
    audited: number;
    leak_checks: number;
    leaks: { boundary: string; note: string }[];
    duplicates?: number;
  }[];
}

export interface AppConfig {
  planner: string;
  planner_provider: string;
  headless: boolean;
  viewport: number[];
  approval_ttl: number;
  home_url: string;
  canary_registered: boolean;
}