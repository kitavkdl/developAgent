import type {
  CacheDecision,
  JobViewState,
  TableRows,
  TraceLine,
  VerdictEnum,
} from "@/types/domain";
import type { ResearchEvent, ResearchEventType } from "@/types/events";

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
  /** Latest event type for stage focus mapping. */
  lastEventType: ResearchEventType | null;
  /** Entity ids that should pulse (claim, search run, evidence, verdict). */
  focusEntityIds: string[];
  activeTraceId: string | null;
  activeSearchRunId: string | null;
  /** Evidence/source ids shown as cache reuse (dim). */
  reusedEntityIds: string[];
  /** Evidence/source ids from delta refresh (highlight). */
  freshEntityIds: string[];
  /** After HIT_STALE, first tool.call starts delta path. */
  deltaRefreshStarted: boolean;
  /** True once job.completed — trigger final fitView. */
  growthComplete: boolean;
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
    lastEventType: null,
    focusEntityIds: [],
    activeTraceId: null,
    activeSearchRunId: null,
    reusedEntityIds: [],
    freshEntityIds: [],
    deltaRefreshStarted: false,
    growthComplete: false,
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
      relatedEntityId: line.relatedEntityId,
    },
  ];
}

function withFocus(
  next: JobViewModel,
  entityIds: string[],
  traceId?: string | null,
): void {
  next.focusEntityIds = entityIds;
  if (traceId !== undefined) next.activeTraceId = traceId;
  else if (next.traces.length) {
    next.activeTraceId = next.traces[next.traces.length - 1]?.id ?? null;
  }
}

function markReuseOrFresh(next: JobViewModel, entityIds: string[]): void {
  const isFreshHit = next.cacheDecision === "HIT_FRESH";
  const isStaleReuse =
    next.cacheDecision === "HIT_STALE" && !next.deltaRefreshStarted;
  const isStaleDelta =
    next.cacheDecision === "HIT_STALE" && next.deltaRefreshStarted;

  if (isFreshHit || isStaleReuse) {
    next.reusedEntityIds = Array.from(
      new Set([...next.reusedEntityIds, ...entityIds]),
    );
  } else if (isStaleDelta) {
    next.freshEntityIds = Array.from(
      new Set([...next.freshEntityIds, ...entityIds]),
    );
  }
}

export function applyResearchEvent(
  state: JobViewModel,
  event: ResearchEvent,
): JobViewModel {
  const next: JobViewModel = {
    ...state,
    events: [...state.events, event],
    lastEventType: event.type,
    growthComplete: false,
    tables: {
      claims: [...state.tables.claims],
      sources: [...state.tables.sources],
      evidence_units: [...state.tables.evidence_units],
      verdict_versions: [...state.tables.verdict_versions],
      search_runs: [...state.tables.search_runs],
    },
    reusedEntityIds: [...state.reusedEntityIds],
    freshEntityIds: [...state.freshEntityIds],
    focusEntityIds: [],
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
      withFocus(next, []);
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
        relatedEntityId: event.payload.claim_id,
      });
      withFocus(next, [event.payload.claim_id]);
      break;

    case "cache.candidate":
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "system",
        summary: `Cache candidates · ${event.payload.candidate_claim_ids.length}`,
        created_at: event.created_at,
      });
      withFocus(next, next.tables.claims[0] ? [next.tables.claims[0].id] : []);
      break;

    case "cache.decision":
      next.cacheDecision = event.payload.decision;
      next.reusedEvidenceCount = event.payload.reused_evidence_count ?? null;
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "system",
        summary: `Cache decision · ${event.payload.decision}`,
        created_at: event.created_at,
        relatedEntityId: next.tables.claims[0]?.id,
      });
      withFocus(next, next.tables.claims[0] ? [next.tables.claims[0].id] : []);
      break;

    case "tool.call": {
      const runId =
        event.payload.search_run_id ??
        `run-${event.sequence}-${event.payload.tool_name}`;
      if (next.cacheDecision === "HIT_STALE") {
        next.deltaRefreshStarted = true;
      }
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
      next.activeSearchRunId = runId;
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "tool.call",
        agent_label: event.payload.agent_label,
        summary: `${event.payload.tool_name}(${JSON.stringify(event.payload.args_redacted)})`,
        created_at: event.created_at,
        relatedEntityId: runId,
      });
      withFocus(next, [runId]);
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
        next.activeSearchRunId = runId;
      }
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "tool.result",
        summary: event.payload.result_summary,
        created_at: event.created_at,
        relatedEntityId: runId,
      });
      withFocus(next, runId ? [runId] : []);
      break;
    }

    case "evidence.extracted": {
      const ev = event.payload;
      next.tables.evidence_units.push(ev);
      const linked: string[] = [ev.evidence_id];
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
      if (ev.source_id) linked.push(ev.source_id);
      markReuseOrFresh(next, linked);
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "system",
        summary: `Evidence · ${ev.title ?? ev.evidence_id}`,
        created_at: event.created_at,
        relatedEntityId: ev.evidence_id,
      });
      withFocus(next, linked);
      break;
    }

    case "verdict.updated": {
      const verdictId = `verdict-${event.sequence}`;
      next.verdict = event.payload.verdict;
      next.reasonCodes = event.payload.reason_codes ?? [];
      next.tables.verdict_versions.push({
        id: verdictId,
        verdict: event.payload.verdict,
        evidence_ids: event.payload.evidence_ids,
        evaluated_at: event.created_at,
      });
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "system",
        summary: `Verdict · ${event.payload.verdict}`,
        created_at: event.created_at,
        relatedEntityId: verdictId,
      });
      withFocus(next, [verdictId, ...event.payload.evidence_ids]);
      break;
    }

    case "answer.delta":
      next.answer += event.payload.text_delta;
      if (event.payload.citation_evidence_ids?.length) {
        next.citationEvidenceIds = Array.from(
          new Set([
            ...next.citationEvidenceIds,
            ...event.payload.citation_evidence_ids,
          ]),
        );
        withFocus(next, event.payload.citation_evidence_ids);
      }
      break;

    case "job.completed":
      next.status =
        event.payload.status === "degraded" ? "degraded" : "complete";
      next.growthComplete = true;
      next.activeSearchRunId = null;
      next.focusEntityIds = [];
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "system",
        summary: `Job ${event.payload.status}`,
        created_at: event.created_at,
      });
      withFocus(next, [], next.traces[next.traces.length - 1]?.id ?? null);
      break;

    case "job.failed":
      next.status = "failed";
      next.errorMessage = event.payload.message;
      next.growthComplete = true;
      next.focusEntityIds = [];
      break;
  }

  return next;
}
