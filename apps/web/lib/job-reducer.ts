import type {
  CacheDecision,
  JobViewState,
  TableRows,
  TraceLine,
  VerdictEnum,
} from "@/types/domain";
import type { ResearchEvent } from "@/types/events";

export interface JobViewModel {
  jobId: string | null;
  query: string;
  status: JobViewState;
  cacheDecision: CacheDecision | null;
  reusedEvidenceCount: number | null;
  verdict: VerdictEnum | null;
  reasonCodes: string[];
  answer: string;
  citationEvidenceIds: string[];
  errorMessage: string | null;
  events: ResearchEvent[];
  traces: TraceLine[];
  tables: TableRows;
}

export function createInitialJobView(query = ""): JobViewModel {
  return {
    jobId: null,
    query,
    status: "idle",
    cacheDecision: null,
    reusedEvidenceCount: null,
    verdict: null,
    reasonCodes: [],
    answer: "",
    citationEvidenceIds: [],
    errorMessage: null,
    events: [],
    traces: [],
    tables: {
      claims: [],
      sources: [],
      evidence_units: [],
      verdict_versions: [],
      search_runs: [],
    },
  };
}

function pushTrace(
  state: JobViewModel,
  line: Omit<TraceLine, "id"> & { id?: string },
): TraceLine[] {
  return [
    ...state.traces,
    {
      id: line.id ?? `trace-${line.sequence}`,
      sequence: line.sequence,
      kind: line.kind,
      agent_label: line.agent_label,
      summary: line.summary,
      created_at: line.created_at,
    },
  ];
}

export function applyResearchEvent(
  state: JobViewModel,
  event: ResearchEvent,
): JobViewModel {
  const next: JobViewModel = {
    ...state,
    events: [...state.events, event],
    tables: {
      claims: [...state.tables.claims],
      sources: [...state.tables.sources],
      evidence_units: [...state.tables.evidence_units],
      verdict_versions: [...state.tables.verdict_versions],
      search_runs: [...state.tables.search_runs],
    },
  };

  switch (event.type) {
    case "job.created":
      next.jobId = event.job_id;
      next.status = "streaming";
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "system",
        summary: "Job created",
        created_at: event.created_at,
      });
      break;

    case "claim.normalized":
      next.tables.claims.push({
        id: event.payload.claim_id,
        signature_summary: event.payload.signature_summary,
        created_at: event.created_at,
      });
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "system",
        summary: `Normalized claim · ${event.payload.signature_summary}`,
        created_at: event.created_at,
      });
      break;

    case "cache.candidate":
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "system",
        summary: `Cache candidates · ${event.payload.candidate_claim_ids.length}`,
        created_at: event.created_at,
      });
      break;

    case "cache.decision":
      next.cacheDecision = event.payload.decision;
      next.reusedEvidenceCount = event.payload.reused_evidence_count ?? null;
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "system",
        summary: `Cache decision · ${event.payload.decision}`,
        created_at: event.created_at,
      });
      break;

    case "tool.call": {
      const runId =
        event.payload.search_run_id ?? `run-${event.sequence}-${event.payload.tool_name}`;
      if (!next.tables.search_runs.some((r) => r.id === runId)) {
        next.tables.search_runs.push({
          id: runId,
          provider: event.payload.tool_name.includes("scholar")
            ? "scholar"
            : "web",
          query: String(event.payload.args_redacted.query ?? ""),
          status: "running",
        });
      }
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "tool.call",
        agent_label: event.payload.agent_label,
        summary: `${event.payload.tool_name}(${JSON.stringify(event.payload.args_redacted)})`,
        created_at: event.created_at,
      });
      break;
    }

    case "tool.result": {
      const runId = event.payload.search_run_id;
      if (runId) {
        next.tables.search_runs = next.tables.search_runs.map((r) =>
          r.id === runId
            ? { ...r, status: event.payload.ok ? "ok" : "failed" }
            : r,
        );
      }
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "tool.result",
        summary: event.payload.result_summary,
        created_at: event.created_at,
      });
      break;
    }

    case "evidence.extracted": {
      const ev = event.payload;
      next.tables.evidence_units.push(ev);
      if (
        ev.source_id &&
        !next.tables.sources.some((s) => s.id === ev.source_id)
      ) {
        next.tables.sources.push({
          id: ev.source_id,
          title: ev.title ?? ev.source_id,
          url: ev.url,
          access_level: ev.access_level,
        });
      }
      break;
    }

    case "verdict.updated":
      next.verdict = event.payload.verdict;
      next.reasonCodes = event.payload.reason_codes ?? [];
      next.tables.verdict_versions.push({
        id: `verdict-${event.sequence}`,
        verdict: event.payload.verdict,
        evidence_ids: event.payload.evidence_ids,
        evaluated_at: event.created_at,
      });
      break;

    case "answer.delta":
      next.answer += event.payload.text_delta;
      if (event.payload.citation_evidence_ids?.length) {
        next.citationEvidenceIds = Array.from(
          new Set([
            ...next.citationEvidenceIds,
            ...event.payload.citation_evidence_ids,
          ]),
        );
      }
      break;

    case "job.completed":
      next.status =
        event.payload.status === "degraded" ? "degraded" : "complete";
      break;

    case "job.failed":
      next.status = "failed";
      next.errorMessage = event.payload.message;
      break;
  }

  return next;
}
