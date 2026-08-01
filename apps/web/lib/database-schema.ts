export type DatabaseVisibility = "shared-public" | "tenant-private";

export interface DatabaseTableDefinition {
  id: string;
  label: string;
  description: string;
  fields: string[];
  visibility: DatabaseVisibility;
  position: { x: number; y: number };
}

export interface DatabaseRelationDefinition {
  id: string;
  source: string;
  target: string;
  label: string;
  kind: "ownership" | "lineage" | "derivation";
}

export const DATABASE_TABLES: DatabaseTableDefinition[] = [
  {
    id: "research_jobs",
    label: "research_jobs",
    description: "Per-request execution envelope and terminal state.",
    fields: [
      "id",
      "tenant_id",
      "raw_query",
      "status",
      "claim_key",
      "timestamps",
      "error",
    ],
    visibility: "tenant-private",
    position: { x: 0, y: 280 },
  },
  {
    id: "claims",
    label: "claims",
    description: "De-identified canonical claim signatures for reuse.",
    fields: [
      "id",
      "canonical signature JSON",
      "embedding",
      "domain",
      "created_at",
    ],
    visibility: "shared-public",
    position: { x: 270, y: 0 },
  },
  {
    id: "search_runs",
    label: "search_runs",
    description: "Bounded provider searches and their coverage window.",
    fields: [
      "claim",
      "provider",
      "channel",
      "query",
      "filters",
      "request ID",
      "status",
      "searched_at",
      "coverage_until",
    ],
    visibility: "tenant-private",
    position: { x: 540, y: 0 },
  },
  {
    id: "sources",
    label: "sources",
    description: "Canonical public source identity, preferring DOI or paper ID.",
    fields: [
      "canonical URL/DOI",
      "title",
      "publisher",
      "publication date",
      "source class",
    ],
    visibility: "shared-public",
    position: { x: 540, y: 360 },
  },
  {
    id: "source_snapshots",
    label: "source_snapshots",
    description: "Immutable captures of accessible source material.",
    fields: [
      "source",
      "content hash",
      "access level",
      "captured text",
      "captured_at",
      "status",
    ],
    visibility: "shared-public",
    position: { x: 810, y: 360 },
  },
  {
    id: "evidence_units",
    label: "evidence_units",
    description: "Versioned evidence evaluation against claim scope.",
    fields: [
      "claim",
      "snapshot",
      "relation",
      "direction",
      "scope JSON",
      "extraction versions",
    ],
    visibility: "shared-public",
    position: { x: 1080, y: 180 },
  },
  {
    id: "verdict_versions",
    label: "verdict_versions",
    description: "Immutable verdict history produced by policy gates.",
    fields: [
      "claim",
      "enum",
      "reason codes",
      "evidence IDs",
      "policy version",
      "evaluated_at",
    ],
    visibility: "shared-public",
    position: { x: 1350, y: 0 },
  },
  {
    id: "answer_versions",
    label: "answer_versions",
    description: "Question-specific answer history and citations.",
    fields: ["job", "current question answer", "citations", "generated_at"],
    visibility: "tenant-private",
    position: { x: 1350, y: 400 },
  },
  {
    id: "trace_events",
    label: "trace_events",
    description: "Ordered, redacted pipeline event stream for a job.",
    fields: [
      "job",
      "sequence",
      "event type",
      "redacted payload",
      "created_at",
    ],
    visibility: "tenant-private",
    position: { x: 270, y: 700 },
  },
];

export const DATABASE_RELATIONS: DatabaseRelationDefinition[] = [
  {
    id: "job-claim",
    source: "research_jobs",
    target: "claims",
    label: "resolves claim_key",
    kind: "derivation",
  },
  {
    id: "job-answer",
    source: "research_jobs",
    target: "answer_versions",
    label: "owns answers",
    kind: "ownership",
  },
  {
    id: "job-trace",
    source: "research_jobs",
    target: "trace_events",
    label: "streams events",
    kind: "ownership",
  },
  {
    id: "claim-search",
    source: "claims",
    target: "search_runs",
    label: "searched by",
    kind: "lineage",
  },
  {
    id: "search-source",
    source: "search_runs",
    target: "sources",
    label: "discovers",
    kind: "lineage",
  },
  {
    id: "source-snapshot",
    source: "sources",
    target: "source_snapshots",
    label: "captured as",
    kind: "lineage",
  },
  {
    id: "claim-evidence",
    source: "claims",
    target: "evidence_units",
    label: "evaluated against",
    kind: "derivation",
  },
  {
    id: "snapshot-evidence",
    source: "source_snapshots",
    target: "evidence_units",
    label: "extracts",
    kind: "derivation",
  },
  {
    id: "evidence-verdict",
    source: "evidence_units",
    target: "verdict_versions",
    label: "aggregates",
    kind: "derivation",
  },
  {
    id: "evidence-answer",
    source: "evidence_units",
    target: "answer_versions",
    label: "cited by",
    kind: "lineage",
  },
];
