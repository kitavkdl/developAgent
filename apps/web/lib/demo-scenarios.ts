import type { CandidateView, DemoScenarioId } from "@/types/domain";
import type { ResearchEvent } from "@/types/events";

function iso(offsetMs: number): string {
  return new Date(Date.UTC(2026, 7, 1, 12, 0, 0) + offsetMs).toISOString();
}

function candidate(
  partial: Partial<CandidateView> &
    Pick<CandidateView, "candidate_id" | "title" | "excerpt_or_summary">,
): CandidateView {
  const check = partial.applicability_check ?? {
    scope_match: true,
    metric_match: true,
    timeframe_match: true,
    target_match: true,
  };
  return {
    claim_id: "claim-1",
    source_id: partial.source_id ?? `src-${partial.candidate_id}`,
    url: partial.url ?? "https://example.org/counterexample",
    published_at: partial.published_at ?? "2024-06-01",
    evaluated_at: iso(4000),
    passes_gate: Object.values(check).every(Boolean),
    applicability_check: check,
    ...partial,
  };
}

function withJob(
  jobId: string,
  events: Array<Omit<ResearchEvent, "job_id"> & { job_id?: string }>,
): ResearchEvent[] {
  return events.map((e) => ({ ...e, job_id: jobId })) as ResearchEvent[];
}

function commonHead(jobId: string, query: string) {
  return withJob(jobId, [
    {
      sequence: 1,
      type: "job.created",
      created_at: iso(0),
      payload: { status: "running" },
    },
    {
      sequence: 2,
      type: "intake.completed",
      created_at: iso(200),
      payload: { source_type: "TEXT", brand: "DemoBrand", product: "DemoProduct" },
    },
    {
      sequence: 3,
      type: "claim.extracted",
      created_at: iso(400),
      payload: { claim_id: "claim-1", text: query.slice(0, 160) || "demo claim" },
    },
  ]);
}

export function buildScenarioEvents(
  jobId: string,
  query: string,
  scenario: DemoScenarioId,
): ResearchEvent[] {
  const head = commonHead(jobId, query);

  if (scenario === "puffery") {
    return [
      ...head,
      ...withJob(jobId, [
        {
          sequence: 4,
          type: "claim.triaged",
          created_at: iso(700),
          payload: {
            claim_id: "claim-1",
            triage: "PUFFERY",
            reason: "Subjective taste claim — not falsifiable",
          },
        },
        {
          sequence: 5,
          type: "verdict.assembled",
          created_at: iso(900),
          payload: {
            verdict: "PUFFERY",
            candidate_ids: [],
            query_count: 0,
            summary:
              "주관적 과장(PUFFERY)으로 분류되어 검색을 수행하지 않았습니다. tool_call 0건.",
            reason_codes: ["triage_puffery", "no_search"],
          },
        },
        {
          sequence: 6,
          type: "job.completed",
          created_at: iso(1100),
          payload: { status: "complete" },
        },
      ]),
    ];
  }

  if (scenario === "hit") {
    return [
      ...head,
      ...withJob(jobId, [
        {
          sequence: 4,
          type: "claim.triaged",
          created_at: iso(700),
          payload: {
            claim_id: "claim-1",
            triage: "FALSIFIABLE",
            claim_type: "SUPERLATIVE_FIRST",
          },
        },
        {
          sequence: 5,
          type: "route.decided",
          created_at: iso(900),
          payload: { claim_id: "claim-1", route: "GENERAL" },
        },
        {
          sequence: 6,
          type: "industry.classified",
          created_at: iso(1100),
          payload: {
            category_id: "cat-beauty",
            label: "화장품",
            is_new: false,
            similarity: 0.91,
          },
        },
        {
          sequence: 7,
          type: "cache.decision",
          created_at: iso(1300),
          payload: {
            decision: "HIT",
            reused_candidate_count: 1,
            reason_codes: ["canonical_match", "ttl_fresh"],
          },
        },
        {
          sequence: 8,
          type: "candidate.evaluated",
          created_at: iso(1500),
          payload: candidate({
            candidate_id: "cand-cached-1",
            source_id: "src-cached-1",
            title: "Cached prior counterexample (2024)",
            url: "https://example.org/cached-refutation",
            published_at: "2024-03-12",
            excerpt_or_summary:
              "Previously verified counterexample reused under fresh TTL.",
          }),
        },
        {
          sequence: 9,
          type: "verdict.assembled",
          created_at: iso(1800),
          payload: {
            verdict: "REFUTED",
            candidate_ids: ["cand-cached-1"],
            query_count: 0,
            summary:
              "동일 업종 파티션에서 신선한 캐시 반례를 재사용했습니다. 추가 LINER 검색 없음.",
            reason_codes: ["cache_hit", "gate_passed"],
          },
        },
        {
          sequence: 10,
          type: "job.completed",
          created_at: iso(2000),
          payload: { status: "complete" },
        },
      ]),
    ];
  }

  if (scenario === "delta") {
    return [
      ...head,
      ...withJob(jobId, [
        {
          sequence: 4,
          type: "claim.triaged",
          created_at: iso(600),
          payload: {
            claim_id: "claim-1",
            triage: "FALSIFIABLE",
            claim_type: "RANKING",
          },
        },
        {
          sequence: 5,
          type: "route.decided",
          created_at: iso(800),
          payload: { claim_id: "claim-1", route: "GENERAL" },
        },
        {
          sequence: 6,
          type: "industry.classified",
          created_at: iso(1000),
          payload: {
            category_id: "cat-beauty",
            label: "화장품",
            is_new: false,
            similarity: 0.88,
          },
        },
        {
          sequence: 7,
          type: "cache.decision",
          created_at: iso(1200),
          payload: {
            decision: "DELTA",
            reused_candidate_count: 1,
            reason_codes: ["canonical_match", "ttl_expired"],
          },
        },
        {
          sequence: 8,
          type: "candidate.evaluated",
          created_at: iso(1400),
          payload: candidate({
            candidate_id: "cand-stale-1",
            source_id: "src-stale",
            title: "Previously checked source",
            url: "https://example.org/old",
            published_at: "2023-01-10",
            excerpt_or_summary: "Shown first as previously checked (dim).",
          }),
        },
        {
          sequence: 9,
          type: "tool.call",
          created_at: iso(1700),
          payload: {
            tool_name: "liner_web_search",
            agent_label: "Web Agent",
            provider: "liner",
            args_redacted: { query: `${query} after:2024-01-01`, date_from: "2024-01-01" },
            search_run_id: "run-web-1",
          },
        },
        {
          sequence: 10,
          type: "tool.result",
          created_at: iso(2300),
          payload: {
            tool_name: "liner_web_search",
            provider: "liner",
            ok: true,
            result_summary: "2 delta web hits (redacted)",
            provider_request_id: "liner-web-d1",
            search_run_id: "run-web-1",
          },
        },
        {
          sequence: 11,
          type: "candidate.evaluated",
          created_at: iso(2700),
          payload: candidate({
            candidate_id: "cand-delta-1",
            source_id: "src-web-1",
            title: "Updated market ranking notice (2025)",
            url: "https://example.org/notice-2025",
            published_at: "2025-11-02",
            excerpt_or_summary: "Delta counterexample after stale refresh.",
          }),
        },
        {
          sequence: 12,
          type: "verdict.assembled",
          created_at: iso(3100),
          payload: {
            verdict: "REFUTED",
            candidate_ids: ["cand-stale-1", "cand-delta-1"],
            query_count: 1,
            summary:
              "TTL 초과로 델타 검색을 수행했고, 필수 필드를 충족하는 반례가 확인되었습니다.",
            reason_codes: ["delta_refresh", "gate_passed"],
          },
        },
        {
          sequence: 13,
          type: "job.completed",
          created_at: iso(3300),
          payload: { status: "complete" },
        },
      ]),
    ];
  }

  if (scenario === "scholar") {
    return [
      ...head,
      ...withJob(jobId, [
        {
          sequence: 4,
          type: "claim.triaged",
          created_at: iso(700),
          payload: {
            claim_id: "claim-1",
            triage: "FALSIFIABLE",
            claim_type: "CLINICAL_COMPLETION",
          },
        },
        {
          sequence: 5,
          type: "route.decided",
          created_at: iso(900),
          payload: { claim_id: "claim-1", route: "SCIENTIFIC" },
        },
        {
          sequence: 6,
          type: "industry.classified",
          created_at: iso(1100),
          payload: {
            category_id: "cat-pharma",
            label: "건강기능식품",
            is_new: false,
            similarity: 0.86,
          },
        },
        {
          sequence: 7,
          type: "cache.decision",
          created_at: iso(1300),
          payload: { decision: "MISS", reason_codes: ["no_eligible_candidate"] },
        },
        {
          sequence: 8,
          type: "tool.call",
          created_at: iso(1600),
          payload: {
            tool_name: "liner_scholar_search",
            agent_label: "Scholar Agent",
            provider: "liner",
            args_redacted: { query, channel: "scholar" },
            search_run_id: "run-scholar-1",
          },
        },
        {
          sequence: 9,
          type: "tool.result",
          created_at: iso(2400),
          payload: {
            tool_name: "liner_scholar_search",
            provider: "liner",
            ok: true,
            result_summary: "3 scholar hits (snippet-level)",
            provider_request_id: "liner-sch-1",
            search_run_id: "run-scholar-1",
          },
        },
        {
          sequence: 10,
          type: "candidate.evaluated",
          created_at: iso(2800),
          payload: candidate({
            candidate_id: "cand-sch-1",
            source_id: "src-sch-1",
            title: "RCT abstract without matching endpoint",
            url: "https://doi.org/10.1000/demo.scholar.1",
            published_at: "2022-08-01",
            excerpt_or_summary: "Metric does not match advertised clinical claim.",
            applicability_check: {
              scope_match: true,
              metric_match: false,
              timeframe_match: true,
              target_match: true,
            },
          }),
        },
        {
          sequence: 11,
          type: "verdict.assembled",
          created_at: iso(3200),
          payload: {
            verdict: "NOT_REFUTED",
            candidate_ids: ["cand-sch-1"],
            query_count: 1,
            summary:
              "우리가 실행한 1개 Scholar 쿼리에서 falsifier 기준을 전부 충족하는 반례를 찾지 못했습니다. 이 결과는 주장이 사실임을 뜻하지 않습니다.",
            reason_codes: ["gate_failed", "metric_mismatch"],
          },
        },
        {
          sequence: 12,
          type: "job.completed",
          created_at: iso(3400),
          payload: { status: "complete" },
        },
      ]),
    ];
  }

  // miss (default full GENERAL loop → REFUTED)
  return [
    ...head,
    ...withJob(jobId, [
      {
        sequence: 4,
        type: "claim.triaged",
        created_at: iso(600),
        payload: {
          claim_id: "claim-1",
          triage: "FALSIFIABLE",
          claim_type: "SUPERLATIVE_FIRST",
        },
      },
      {
        sequence: 5,
        type: "route.decided",
        created_at: iso(800),
        payload: { claim_id: "claim-1", route: "GENERAL" },
      },
      {
        sequence: 6,
        type: "industry.classified",
        created_at: iso(1000),
        payload: {
          category_id: "cat-beauty",
          label: "화장품",
          is_new: true,
          similarity: null,
        },
      },
      {
        sequence: 7,
        type: "cache.decision",
        created_at: iso(1200),
        payload: { decision: "MISS", reason_codes: ["no_eligible_candidate"] },
      },
      {
        sequence: 8,
        type: "tool.call",
        created_at: iso(1500),
        payload: {
          tool_name: "liner_web_search",
          agent_label: "Web Agent",
          provider: "liner",
          args_redacted: { query: `${query} 국내 최초 선행`, max_results: 5 },
          search_run_id: "run-web-1",
        },
      },
      {
        sequence: 9,
        type: "tool.result",
        created_at: iso(2200),
        payload: {
          tool_name: "liner_web_search",
          provider: "liner",
          ok: true,
          result_summary: "5 web results with visible citations",
          provider_request_id: "liner-web-42",
          search_run_id: "run-web-1",
        },
      },
      {
        sequence: 10,
        type: "tool.call",
        created_at: iso(2400),
        payload: {
          tool_name: "liner_web_search",
          agent_label: "Web Agent",
          provider: "liner",
          args_redacted: { query: `${query} 경쟁사 출시`, max_results: 5 },
          search_run_id: "run-web-2",
        },
      },
      {
        sequence: 11,
        type: "tool.result",
        created_at: iso(3000),
        payload: {
          tool_name: "liner_web_search",
          provider: "liner",
          ok: true,
          result_summary: "4 web results",
          search_run_id: "run-web-2",
        },
      },
      {
        sequence: 12,
        type: "candidate.evaluated",
        created_at: iso(3300),
        payload: candidate({
          candidate_id: "cand-1",
          source_id: "src-1",
          title: "Prior launch article (2019)",
          url: "https://example.org/prior-2019",
          published_at: "2019-04-18",
          excerpt_or_summary:
            "Earlier product launch in the same category undermines '국내 최초'.",
        }),
      },
      {
        sequence: 13,
        type: "candidate.evaluated",
        created_at: iso(3600),
        payload: candidate({
          candidate_id: "cand-2",
          source_id: "src-2",
          title: "Undated blog post",
          url: "https://example.org/undated",
          published_at: null,
          excerpt_or_summary: "Similar claim but no publish date — timeframe fails.",
          applicability_check: {
            scope_match: true,
            metric_match: true,
            timeframe_match: false,
            target_match: true,
          },
        }),
      },
      {
        sequence: 14,
        type: "verdict.assembled",
        created_at: iso(4000),
        payload: {
          verdict: "REFUTED",
          candidate_ids: ["cand-1"],
          query_count: 2,
          summary:
            "필수 매치 필드를 모두 충족하는 반례 문서가 확인되어 REFUTED입니다. (게이트 미통과 후보는 승격되지 않음)",
          reason_codes: ["gate_passed", "prior_instance"],
        },
      },
      {
        sequence: 15,
        type: "job.completed",
        created_at: iso(4200),
        payload: { status: "complete" },
      },
    ]),
  ];
}

export function inferScenarioFromQuery(
  query: string,
  explicit?: DemoScenarioId,
): DemoScenarioId {
  if (explicit) return explicit;
  const q = query.toLowerCase();
  if (/\b(맛있|최고로 맛|feel|감성)\b/.test(q) || /맛있다/.test(query)) {
    return "puffery";
  }
  if (/\b(latest|today|current|new|최신)\b/.test(q)) return "delta";
  if (/\b(reuse|cached|again|다시)\b/.test(q)) return "hit";
  if (/\b(clinical|임상|과학적으로|논문)\b/.test(q)) return "scholar";
  return "miss";
}
