export type DemoScenarioId = "fresh" | "stale" | "miss" | "seed";

export type JobViewState =
  | "idle"
  | "submitting"
  | "streaming"
  | "complete"
  | "failed"
  | "degraded";

export type CacheDecision =
  | "HIT_FRESH"
  | "HIT_STALE"
  | "SEED_ONLY"
  | "MISS"
  | "INVALID";

export type VerdictEnum = "Direct" | "Partial" | "Mixed" | "Not found";

export type AccessLevel = "metadata" | "snippet" | "abstract" | "full_text";
export type EvidenceRelation =
  | "direct"
  | "broader"
  | "narrower"
  | "conflicting"
  | "unrelated";
export type EvidenceDirection = "supports" | "refutes" | "mixed" | "background";

export type GraphNodeKind =
  | "Claim"
  | "SearchRun"
  | "Source"
  | "EvidenceUnit"
  | "Verdict";

export interface EvidenceUnitView {
  evidence_id: string;
  claim_id: string;
  source_snapshot_id: string;
  source_id?: string;
  title?: string;
  url?: string;
  access_level: AccessLevel;
  relation: EvidenceRelation;
  direction: EvidenceDirection;
  matched_scope?: Record<string, string | undefined>;
  missing_scope?: string[];
  excerpt_or_summary: string;
  extracted_at: string;
}

export interface JobSnapshot {
  job_id: string;
  query: string;
  status: JobViewState;
  cache_decision?: CacheDecision;
  verdict?: VerdictEnum;
  answer?: string;
}

export interface TraceLine {
  id: string;
  sequence: number;
  kind: "tool.call" | "tool.result" | "system";
  agent_label?: string;
  summary: string;
  created_at: string;
}

export interface TableRows {
  claims: Array<{ id: string; signature_summary: string; created_at: string }>;
  sources: Array<{
    id: string;
    title: string;
    url?: string;
    access_level: AccessLevel;
  }>;
  evidence_units: EvidenceUnitView[];
  verdict_versions: Array<{
    id: string;
    verdict: VerdictEnum;
    evidence_ids: string[];
    evaluated_at: string;
  }>;
  search_runs: Array<{
    id: string;
    provider: string;
    query: string;
    status: string;
  }>;
}

export type GraphNodeData = {
  kind: GraphNodeKind;
  label: string;
  subtitle?: string;
  stale?: boolean;
  access_level?: AccessLevel;
  verdict?: VerdictEnum;
  entityId: string;
  [key: string]: unknown;
};

export type TableTab =
  | "claims"
  | "evidence_units"
  | "sources"
  | "verdict_versions";
