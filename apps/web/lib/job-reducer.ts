import type {
  CacheDecision,
  JobViewState,
  RouteKind,
  TableRows,
  TraceLine,
  TriageLabel,
  VerdictEnum,
} from "@/types/domain";
import type { ResearchEvent, ResearchEventType } from "@/types/events";

export interface JobViewModel {
  jobId: string | null;
  query: string;
  status: JobViewState;
  cacheDecision: CacheDecision | null;
  reusedCandidateCount: number | null;
  route: RouteKind | null;
  industryLabel: string | null;
  industryIsNew: boolean;
  triage: TriageLabel | null;
  verdict: VerdictEnum | null;
  reasonCodes: string[];
  summary: string;
  queryCount: number;
  citationCandidateIds: string[];
  errorMessage: string | null;
  events: ResearchEvent[];
  traces: TraceLine[];
  tables: TableRows;
  lastEventType: ResearchEventType | null;
  focusEntityIds: string[];
  activeTraceId: string | null;
  activeSearchRunId: string | null;
  reusedEntityIds: string[];
  freshEntityIds: string[];
  deltaRefreshStarted: boolean;
  growthComplete: boolean;
}

export function createInitialJobView(query = ""): JobViewModel {
  return {
    jobId: null,
    query,
    status: "idle",
    cacheDecision: null,
    reusedCandidateCount: null,
    route: null,
    industryLabel: null,
    industryIsNew: false,
    triage: null,
    verdict: null,
    reasonCodes: [],
    summary: "",
    queryCount: 0,
    citationCandidateIds: [],
    errorMessage: null,
    events: [],
    traces: [],
    tables: {
      claims: [],
      sources: [],
      candidates: [],
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
      provider: line.provider,
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
  const isHit = next.cacheDecision === "HIT";
  const isDeltaReuse =
    next.cacheDecision === "DELTA" && !next.deltaRefreshStarted;
  const isDeltaFresh =
    next.cacheDecision === "DELTA" && next.deltaRefreshStarted;

  if (isHit || isDeltaReuse) {
    next.reusedEntityIds = Array.from(
      new Set([...next.reusedEntityIds, ...entityIds]),
    );
  } else if (isDeltaFresh) {
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
      candidates: [...state.tables.candidates],
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

    case "intake.completed":
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "system",
        summary: `Intake · ${event.payload.source_type}`,
        created_at: event.created_at,
      });
      withFocus(next, []);
      break;

    case "claim.extracted":
      next.tables.claims.push({
        id: event.payload.claim_id,
        text: event.payload.text,
        created_at: event.created_at,
      });
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "system",
        summary: `Claim extracted · ${event.payload.text}`,
        created_at: event.created_at,
        relatedEntityId: event.payload.claim_id,
      });
      withFocus(next, [event.payload.claim_id]);
      break;

    case "claim.triaged": {
      next.triage = event.payload.triage;
      next.tables.claims = next.tables.claims.map((c) =>
        c.id === event.payload.claim_id
          ? {
              ...c,
              triage: event.payload.triage,
              claim_type: event.payload.claim_type,
            }
          : c,
      );
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "system",
        summary: `Triage · ${event.payload.triage}${
          event.payload.reason ? ` — ${event.payload.reason}` : ""
        }`,
        created_at: event.created_at,
        relatedEntityId: event.payload.claim_id,
      });
      withFocus(next, [event.payload.claim_id]);
      break;
    }

    case "route.decided":
      next.route = event.payload.route;
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "system",
        summary: `Route · ${event.payload.route}`,
        created_at: event.created_at,
        relatedEntityId: event.payload.claim_id,
      });
      withFocus(next, [event.payload.claim_id]);
      break;

    case "industry.classified":
      next.industryLabel = event.payload.label;
      next.industryIsNew = event.payload.is_new;
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "system",
        summary: `Industry · ${event.payload.label}${
          event.payload.is_new ? " (NEW)" : ""
        }`,
        created_at: event.created_at,
      });
      withFocus(next, next.tables.claims[0] ? [next.tables.claims[0].id] : []);
      break;

    case "cache.decision":
      next.cacheDecision = event.payload.decision;
      next.reusedCandidateCount = event.payload.reused_candidate_count ?? null;
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "system",
        summary: `Cache · ${event.payload.decision}`,
        created_at: event.created_at,
        relatedEntityId: next.tables.claims[0]?.id,
      });
      withFocus(next, next.tables.claims[0] ? [next.tables.claims[0].id] : []);
      break;

    case "tool.call": {
      const runId =
        event.payload.search_run_id ??
        `run-${event.sequence}-${event.payload.tool_name}`;
      if (next.cacheDecision === "DELTA") {
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
        provider: event.payload.provider,
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
        provider: event.payload.provider,
        summary: event.payload.result_summary,
        created_at: event.created_at,
        relatedEntityId: runId,
      });
      withFocus(next, runId ? [runId] : []);
      break;
    }

    case "candidate.evaluated": {
      const cand = event.payload;
      next.tables.candidates.push(cand);
      const linked: string[] = [cand.candidate_id];
      if (
        cand.source_id &&
        !next.tables.sources.some((s) => s.id === cand.source_id)
      ) {
        next.tables.sources.push({
          id: cand.source_id,
          title: cand.title ?? cand.source_id,
          url: cand.url,
          published_at: cand.published_at,
        });
        linked.push(cand.source_id);
      }
      markReuseOrFresh(next, linked);
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "system",
        summary: `Candidate · ${cand.title ?? cand.candidate_id} · gate=${
          cand.passes_gate ? "pass" : "fail"
        }`,
        created_at: event.created_at,
        relatedEntityId: cand.candidate_id,
      });
      withFocus(next, linked);
      break;
    }

    case "verdict.assembled": {
      const verdictId = `verdict-${event.sequence}`;
      next.verdict = event.payload.verdict;
      next.reasonCodes = event.payload.reason_codes ?? [];
      next.summary = event.payload.summary;
      next.queryCount = event.payload.query_count;
      next.citationCandidateIds = event.payload.candidate_ids;
      next.tables.verdict_versions.push({
        id: verdictId,
        verdict: event.payload.verdict,
        candidate_ids: event.payload.candidate_ids,
        query_count: event.payload.query_count,
        summary: event.payload.summary,
        evaluated_at: event.created_at,
      });
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "system",
        summary: `Verdict · ${event.payload.verdict}`,
        created_at: event.created_at,
        relatedEntityId: verdictId,
      });
      withFocus(next, [verdictId, ...event.payload.candidate_ids]);
      break;
    }

    case "job.completed":
      next.status =
        event.payload.status === "degraded" ? "degraded" : "complete";
      next.growthComplete = true;
      next.activeSearchRunId = null;
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "system",
        summary: `Job ${event.payload.status}`,
        created_at: event.created_at,
      });
      withFocus(next, [], next.traces[next.traces.length - 1]?.id ?? null);
      break;

    case "job.degraded":
      next.status = "degraded";
      next.growthComplete = true;
      next.errorMessage = event.payload.reason;
      next.traces = pushTrace(next, {
        sequence: event.sequence,
        kind: "system",
        summary: `Degraded · ${event.payload.reason}`,
        created_at: event.created_at,
      });
      withFocus(next, []);
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
