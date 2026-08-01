export type DemoScenarioId = "miss" | "hit" | "delta" | "puffery" | "scholar";

export type PlaybackSpeed = "slow" | "normal" | "fast";

export type JobViewState =
  | "idle"
  | "submitting"
  | "streaming"
  | "complete"
  | "failed"
  | "degraded";

export type CacheDecision = "HIT" | "MISS" | "DELTA" | "REVERIFY";

export type VerdictEnum =
  | "REFUTED"
  | "NOT_REFUTED"
  | "PUBLIC_SUBSTANTIATION_NOT_FOUND"
  | "PUFFERY";

export type RouteKind = "SCIENTIFIC" | "GENERAL";

export type TriageLabel = "FALSIFIABLE" | "PUFFERY" | "NOT_A_CLAIM";

export type GraphNodeKind =
  | "Claim"
  | "SearchRun"
  | "Source"
  | "Candidate"
  | "Verdict";

export interface ApplicabilityCheck {
  scope_match: boolean;
  metric_match: boolean;
  timeframe_match: boolean;
  target_match: boolean;
}

export interface CandidateView {
  candidate_id: string;
  claim_id: string;
  source_id?: string;
  title?: string;
  url?: string;
  published_at?: string | null;
  excerpt_or_summary: string;
  applicability_check: ApplicabilityCheck;
  passes_gate: boolean;
  evaluated_at: string;
}

export interface JobSnapshot {
  job_id: string;
  query: string;
  status: JobViewState;
  cache_decision?: CacheDecision;
  verdict?: VerdictEnum;
  summary?: string;
}

export interface TraceLine {
  id: string;
  sequence: number;
  kind: "tool.call" | "tool.result" | "system";
  agent_label?: string;
  provider?: "liner" | "openai";
  summary: string;
  created_at: string;
  relatedEntityId?: string;
}

export interface TableRows {
  claims: Array<{
    id: string;
    text: string;
    triage?: TriageLabel;
    claim_type?: string;
    created_at: string;
  }>;
  sources: Array<{
    id: string;
    title: string;
    url?: string;
    published_at?: string | null;
  }>;
  candidates: CandidateView[];
  verdict_versions: Array<{
    id: string;
    verdict: VerdictEnum;
    candidate_ids: string[];
    query_count: number;
    summary: string;
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
  freshDelta?: boolean;
  reused?: boolean;
  pulse?: boolean;
  emphasis?: boolean;
  cacheRing?: CacheDecision | null;
  passesGate?: boolean;
  provider?: string;
  verdict?: VerdictEnum;
  entityId: string;
  [key: string]: unknown;
};

export type TableTab =
  | "claims"
  | "candidates"
  | "sources"
  | "verdict_versions";

export const PLAYBACK_STEP_MS: Record<PlaybackSpeed, number> = {
  slow: 700,
  normal: 420,
  fast: 180,
};
