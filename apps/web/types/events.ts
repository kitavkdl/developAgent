import type {
  CacheDecision,
  CandidateView,
  RouteKind,
  TriageLabel,
  VerdictEnum,
} from "./domain";

export type ResearchEventType =
  | "job.created"
  | "intake.completed"
  | "claim.extracted"
  | "claim.triaged"
  | "route.decided"
  | "industry.classified"
  | "cache.decision"
  | "tool.call"
  | "tool.result"
  | "candidate.evaluated"
  | "verdict.assembled"
  | "job.completed"
  | "job.failed"
  | "job.degraded";

export interface ResearchEventBase {
  job_id: string;
  sequence: number;
  type: ResearchEventType;
  created_at: string;
}

export type ResearchEvent =
  | (ResearchEventBase & {
      type: "job.created";
      payload: { status: string };
    })
  | (ResearchEventBase & {
      type: "intake.completed";
      payload: { source_type: "TEXT" | "IMAGE" | "URL"; brand?: string; product?: string };
    })
  | (ResearchEventBase & {
      type: "claim.extracted";
      payload: { claim_id: string; text: string };
    })
  | (ResearchEventBase & {
      type: "claim.triaged";
      payload: {
        claim_id: string;
        triage: TriageLabel;
        claim_type?: string;
        reason?: string;
      };
    })
  | (ResearchEventBase & {
      type: "route.decided";
      payload: { claim_id: string; route: RouteKind };
    })
  | (ResearchEventBase & {
      type: "industry.classified";
      payload: {
        category_id: string;
        label: string;
        is_new: boolean;
        similarity?: number | null;
      };
    })
  | (ResearchEventBase & {
      type: "cache.decision";
      payload: {
        decision: CacheDecision;
        reused_candidate_count?: number;
        reason_codes?: string[];
      };
    })
  | (ResearchEventBase & {
      type: "tool.call";
      payload: {
        tool_name: string;
        agent_label: string;
        provider: "liner" | "openai";
        args_redacted: Record<string, unknown>;
        search_run_id?: string;
      };
    })
  | (ResearchEventBase & {
      type: "tool.result";
      payload: {
        tool_name: string;
        provider: "liner" | "openai";
        ok: boolean;
        result_summary: string;
        provider_request_id?: string;
        search_run_id?: string;
      };
    })
  | (ResearchEventBase & {
      type: "candidate.evaluated";
      payload: CandidateView;
    })
  | (ResearchEventBase & {
      type: "verdict.assembled";
      payload: {
        verdict: VerdictEnum;
        candidate_ids: string[];
        query_count: number;
        summary: string;
        reason_codes?: string[];
      };
    })
  | (ResearchEventBase & {
      type: "job.completed";
      payload: { status: "complete" | "degraded" };
    })
  | (ResearchEventBase & {
      type: "job.failed";
      payload: { error_code: string; message: string };
    })
  | (ResearchEventBase & {
      type: "job.degraded";
      payload: { reason: string };
    });
