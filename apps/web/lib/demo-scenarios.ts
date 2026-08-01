import type { DemoScenarioId, EvidenceUnitView } from "@/types/domain";
import type { ResearchEvent } from "@/types/events";

function iso(offsetMs: number): string {
  return new Date(Date.UTC(2026, 7, 1, 12, 0, 0) + offsetMs).toISOString();
}

function baseEvidence(
  partial: Partial<EvidenceUnitView> &
    Pick<EvidenceUnitView, "evidence_id" | "source_id" | "title">,
): EvidenceUnitView {
  return {
    claim_id: "claim-1",
    source_snapshot_id: `${partial.source_id}-snap`,
    url: partial.url ?? "https://example.org/paper",
    access_level: "snippet",
    relation: "direct",
    direction: "supports",
    matched_scope: { subject: "product X", outcome: "efficacy" },
    excerpt_or_summary:
      partial.excerpt_or_summary ??
      "Snippet-level excerpt supporting the scoped claim.",
    extracted_at: iso(4000),
    ...partial,
  };
}

function withJob(
  jobId: string,
  events: Array<Omit<ResearchEvent, "job_id"> & { job_id?: string }>,
): ResearchEvent[] {
  return events.map((e) => ({ ...e, job_id: jobId })) as ResearchEvent[];
}

export function buildScenarioEvents(
  jobId: string,
  query: string,
  scenario: DemoScenarioId,
): ResearchEvent[] {
  const commonStart = withJob(jobId, [
    {
      sequence: 1,
      type: "job.created",
      created_at: iso(0),
      payload: { status: "running" },
    },
    {
      sequence: 2,
      type: "claim.normalized",
      created_at: iso(400),
      payload: {
        claim_id: "claim-1",
        signature_summary: query.slice(0, 80) || "demo claim",
      },
    },
  ]);

  if (scenario === "fresh") {
    return [
      ...commonStart,
      ...withJob(jobId, [
        {
          sequence: 3,
          type: "cache.candidate",
          created_at: iso(700),
          payload: { candidate_claim_ids: ["claim-cached-1"], scores: [0.91] },
        },
        {
          sequence: 4,
          type: "cache.decision",
          created_at: iso(900),
          payload: {
            decision: "HIT_FRESH",
            reused_evidence_count: 2,
            reason_codes: ["scope_eligible", "channels_fresh"],
          },
        },
        {
          sequence: 5,
          type: "evidence.extracted",
          created_at: iso(1200),
          payload: baseEvidence({
            evidence_id: "ev-cached-1",
            source_id: "src-1",
            title: "Cached scholar review (2024)",
            url: "https://doi.org/10.1000/demo.fresh.1",
            access_level: "abstract",
            excerpt_or_summary:
              "Previously collected abstract reused under fresh TTL.",
          }),
        },
        {
          sequence: 6,
          type: "evidence.extracted",
          created_at: iso(1500),
          payload: baseEvidence({
            evidence_id: "ev-cached-2",
            source_id: "src-2",
            title: "Official product monograph",
            url: "https://example.org/label",
            access_level: "snippet",
            relation: "broader",
            direction: "supports",
          }),
        },
        {
          sequence: 7,
          type: "verdict.updated",
          created_at: iso(1900),
          payload: {
            verdict: "Partial",
            evidence_ids: ["ev-cached-1", "ev-cached-2"],
            reason_codes: ["reused_fresh", "broader_scope_present"],
          },
        },
        {
          sequence: 8,
          type: "answer.delta",
          created_at: iso(2100),
          payload: {
            text_delta:
              "Eligible cached evidence was reused (2 units). A new contextual answer was generated without external search. ",
            citation_evidence_ids: ["ev-cached-1", "ev-cached-2"],
          },
        },
        {
          sequence: 9,
          type: "answer.delta",
          created_at: iso(2300),
          payload: {
            text_delta:
              "Scope is only partially covered, so the verdict is Partial—not a product-specific Direct claim.",
          },
        },
        {
          sequence: 10,
          type: "job.completed",
          created_at: iso(2500),
          payload: { status: "complete" },
        },
      ]),
    ];
  }

  if (scenario === "stale") {
    return [
      ...commonStart,
      ...withJob(jobId, [
        {
          sequence: 3,
          type: "cache.candidate",
          created_at: iso(600),
          payload: { candidate_claim_ids: ["claim-cached-1"], scores: [0.88] },
        },
        {
          sequence: 4,
          type: "cache.decision",
          created_at: iso(800),
          payload: {
            decision: "HIT_STALE",
            reused_evidence_count: 1,
            reason_codes: ["scope_eligible", "web_channel_expired"],
          },
        },
        {
          sequence: 5,
          type: "evidence.extracted",
          created_at: iso(1000),
          payload: baseEvidence({
            evidence_id: "ev-stale-1",
            source_id: "src-stale",
            title: "Previously checked source",
            url: "https://example.org/old",
            access_level: "snippet",
            excerpt_or_summary: "Shown immediately as previously checked.",
          }),
        },
        {
          sequence: 6,
          type: "tool.call",
          created_at: iso(1400),
          payload: {
            tool_name: "web_search",
            agent_label: "Web Agent",
            args_redacted: { query: `${query} latest`, max_results: 5 },
            search_run_id: "run-web-1",
          },
        },
        {
          sequence: 7,
          type: "tool.result",
          created_at: iso(2000),
          payload: {
            tool_name: "web_search",
            ok: true,
            result_summary: "3 current web sources (redacted)",
            provider_request_id: "web-req-1",
            search_run_id: "run-web-1",
          },
        },
        {
          sequence: 8,
          type: "evidence.extracted",
          created_at: iso(2400),
          payload: baseEvidence({
            evidence_id: "ev-fresh-web",
            source_id: "src-web-1",
            title: "Updated official notice (2026)",
            url: "https://example.org/notice-2026",
            access_level: "snippet",
            direction: "supports",
            excerpt_or_summary: "Delta web evidence after stale refresh.",
          }),
        },
        {
          sequence: 9,
          type: "verdict.updated",
          created_at: iso(2800),
          payload: {
            verdict: "Direct",
            evidence_ids: ["ev-stale-1", "ev-fresh-web"],
            reason_codes: ["delta_refresh_ok", "scope_matched"],
          },
        },
        {
          sequence: 10,
          type: "answer.delta",
          created_at: iso(3000),
          payload: {
            text_delta:
              "Cached cards were shown first as previously checked, then replaced after a delta web search. ",
            citation_evidence_ids: ["ev-stale-1", "ev-fresh-web"],
          },
        },
        {
          sequence: 11,
          type: "answer.delta",
          created_at: iso(3200),
          payload: {
            text_delta:
              "With refreshed coverage, the aggregated verdict is Direct.",
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

  if (scenario === "seed") {
    return [
      ...commonStart,
      ...withJob(jobId, [
        {
          sequence: 3,
          type: "cache.candidate",
          created_at: iso(700),
          payload: { candidate_claim_ids: ["claim-near-1"], scores: [0.72] },
        },
        {
          sequence: 4,
          type: "cache.decision",
          created_at: iso(900),
          payload: {
            decision: "SEED_ONLY",
            reason_codes: ["partial_scope"],
          },
        },
        {
          sequence: 5,
          type: "tool.call",
          created_at: iso(1200),
          payload: {
            tool_name: "scholar_search",
            agent_label: "Scholar Agent",
            args_redacted: { query, channel: "direct" },
            search_run_id: "run-scholar-1",
          },
        },
        {
          sequence: 6,
          type: "tool.result",
          created_at: iso(1800),
          payload: {
            tool_name: "scholar_search",
            ok: true,
            result_summary: "2 scholar hits (snippet)",
            search_run_id: "run-scholar-1",
          },
        },
        {
          sequence: 7,
          type: "evidence.extracted",
          created_at: iso(2200),
          payload: baseEvidence({
            evidence_id: "ev-seed-1",
            source_id: "src-seed-1",
            title: "Ingredient-family study",
            relation: "broader",
            direction: "supports",
            access_level: "snippet",
          }),
        },
        {
          sequence: 8,
          type: "verdict.updated",
          created_at: iso(2600),
          payload: {
            verdict: "Partial",
            evidence_ids: ["ev-seed-1"],
            reason_codes: ["seed_plan_only", "no_old_verdict_reuse"],
          },
        },
        {
          sequence: 9,
          type: "answer.delta",
          created_at: iso(2800),
          payload: {
            text_delta:
              "Near-match cache seeded the research plan only. Prior verdicts were not reused. ",
            citation_evidence_ids: ["ev-seed-1"],
          },
        },
        {
          sequence: 10,
          type: "job.completed",
          created_at: iso(3000),
          payload: { status: "complete" },
        },
      ]),
    ];
  }

  // miss (default full loop)
  return [
    ...commonStart,
    ...withJob(jobId, [
      {
        sequence: 3,
        type: "cache.candidate",
        created_at: iso(600),
        payload: { candidate_claim_ids: [], scores: [] },
      },
      {
        sequence: 4,
        type: "cache.decision",
        created_at: iso(800),
        payload: { decision: "MISS", reason_codes: ["no_eligible_candidate"] },
      },
      {
        sequence: 5,
        type: "tool.call",
        created_at: iso(1100),
        payload: {
          tool_name: "scholar_search",
          agent_label: "Scholar Agent",
          args_redacted: { query, channel: "direct" },
          search_run_id: "run-scholar-1",
        },
      },
      {
        sequence: 6,
        type: "tool.result",
        created_at: iso(1700),
        payload: {
          tool_name: "scholar_search",
          ok: true,
          result_summary: "4 scholar results (snippet-level)",
          provider_request_id: "liner-req-42",
          search_run_id: "run-scholar-1",
        },
      },
      {
        sequence: 7,
        type: "tool.call",
        created_at: iso(1900),
        payload: {
          tool_name: "web_search",
          agent_label: "Web Agent",
          args_redacted: { query, channel: "current_web" },
          search_run_id: "run-web-1",
        },
      },
      {
        sequence: 8,
        type: "tool.result",
        created_at: iso(2400),
        payload: {
          tool_name: "web_search",
          ok: true,
          result_summary: "5 web results with visible citations",
          search_run_id: "run-web-1",
        },
      },
      {
        sequence: 9,
        type: "evidence.extracted",
        created_at: iso(2700),
        payload: baseEvidence({
          evidence_id: "ev-1",
          source_id: "src-s1",
          title: "Randomized trial abstract",
          url: "https://doi.org/10.1000/demo.miss.1",
          access_level: "snippet",
          relation: "direct",
          direction: "supports",
        }),
      },
      {
        sequence: 10,
        type: "evidence.extracted",
        created_at: iso(3000),
        payload: baseEvidence({
          evidence_id: "ev-2",
          source_id: "src-w1",
          title: "Manufacturer FAQ",
          url: "https://example.org/faq",
          access_level: "snippet",
          relation: "narrower",
          direction: "mixed",
        }),
      },
      {
        sequence: 11,
        type: "evidence.extracted",
        created_at: iso(3300),
        payload: baseEvidence({
          evidence_id: "ev-3",
          source_id: "src-s2",
          title: "Counter-analysis preprint",
          url: "https://doi.org/10.1000/demo.miss.2",
          access_level: "snippet",
          relation: "conflicting",
          direction: "refutes",
          excerpt_or_summary: "Snippet that conflicts on outcome measurement.",
        }),
      },
      {
        sequence: 12,
        type: "verdict.updated",
        created_at: iso(3700),
        payload: {
          verdict: "Mixed",
          evidence_ids: ["ev-1", "ev-2", "ev-3"],
          reason_codes: ["support_and_refute", "snippet_access_only"],
        },
      },
      {
        sequence: 13,
        type: "answer.delta",
        created_at: iso(3900),
        payload: {
          text_delta:
            "Bounded Scholar and Web research found supporting and conflicting snippet-level evidence. ",
          citation_evidence_ids: ["ev-1", "ev-3"],
        },
      },
      {
        sequence: 14,
        type: "answer.delta",
        created_at: iso(4100),
        payload: {
          text_delta:
            "The deterministic aggregate is Mixed. Access level remains snippet—full-study claims are not asserted.",
        },
      },
      {
        sequence: 15,
        type: "job.completed",
        created_at: iso(4300),
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
  if (/\b(latest|today|current|new)\b/.test(q)) return "stale";
  if (/\b(reuse|cached|again)\b/.test(q)) return "fresh";
  if (/\b(family|ingredient|similar)\b/.test(q)) return "seed";
  return "miss";
}
