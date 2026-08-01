import type { CacheDecision, EvidenceUnitView, VerdictEnum } from "./domain";

export type ResearchEventType =
  | "job.created"
  | "claim.normalized"
  | "cache.candidate"
  | "cache.decision"
  | "tool.call"
  | "tool.result"
  | "evidence.extracted"
  | "verdict.updated"
  | "answer.delta"
  | "job.completed"
  | "job.failed";

export interface ResearchEventBase {
  job_id: string;
  sequence: number;
  type: ResearchEventType;
  created_at: string;
}

export type ResearchEvent =
  | (ResearchEventBase & { type: "job.created"; payload: { status: string } })
  | (ResearchEventBase & {
      type: "claim.normalized";
      payload: { claim_id: string; signature_summary: string };
    })
  | (ResearchEventBase & {
      type: "cache.candidate";
      payload: { candidate_claim_ids: string[]; scores?: number[] };
    })
  | (ResearchEventBase & {
      type: "cache.decision";
      payload: {
        decision: CacheDecision;
        reused_evidence_count?: number;
        reason_codes?: string[];
      };
    })
  | (ResearchEventBase & {
      type: "tool.call";
      payload: {
        tool_name: string;
        agent_label: string;
        args_redacted: Record<string, unknown>;
        search_run_id?: string;
      };
    })
  | (ResearchEventBase & {
      type: "tool.result";
      payload: {
        tool_name: string;
        ok: boolean;
        result_summary: string;
        provider_request_id?: string;
        search_run_id?: string;
      };
    })
  | (ResearchEventBase & {
      type: "evidence.extracted";
      payload: EvidenceUnitView;
    })
  | (ResearchEventBase & {
      type: "verdict.updated";
      payload: {
        verdict: VerdictEnum;
        evidence_ids: string[];
        reason_codes?: string[];
      };
    })
  | (ResearchEventBase & {
      type: "answer.delta";
      payload: { text_delta: string; citation_evidence_ids?: string[] };
    })
  | (ResearchEventBase & {
      type: "job.completed";
      payload: { status: "complete" | "degraded" };
    })
  | (ResearchEventBase & {
      type: "job.failed";
      payload: { error_code: string; message: string };
    });
