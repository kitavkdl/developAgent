import type { Edge, Node } from "@xyflow/react";
import type { GraphNodeData, JobViewState } from "@/types/domain";
import type { JobViewModel } from "./job-reducer";

function node(
  id: string,
  data: GraphNodeData,
  position: { x: number; y: number },
): Node {
  return {
    id,
    type: "evidence",
    position,
    data,
  };
}

export function mapJobToGraph(model: JobViewModel): {
  nodes: Node[];
  edges: Edge[];
} {
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  const stale = model.cacheDecision === "HIT_STALE";
  const claim = model.tables.claims[0];

  if (claim) {
    nodes.push(
      node(
        claim.id,
        {
          kind: "Claim",
          label: "Claim",
          subtitle: claim.signature_summary,
          entityId: claim.id,
          stale: stale && model.status === "streaming",
        },
        { x: 280, y: 40 },
      ),
    );
  }

  model.tables.search_runs.forEach((run, i) => {
    const id = run.id;
    nodes.push(
      node(
        id,
        {
          kind: "SearchRun",
          label: run.provider === "scholar" ? "Scholar" : "Web",
          subtitle: run.query || run.status,
          entityId: id,
        },
        { x: 80 + i * 360, y: 180 },
      ),
    );
    if (claim) {
      edges.push({
        id: `${claim.id}-${id}`,
        source: claim.id,
        target: id,
        animated: run.status === "running",
      });
    }
  });

  model.tables.sources.forEach((source, i) => {
    nodes.push(
      node(
        source.id,
        {
          kind: "Source",
          label: "Source",
          subtitle: source.title,
          access_level: source.access_level,
          entityId: source.id,
          stale: stale && model.status === "streaming" && i === 0,
        },
        { x: 40 + i * 220, y: 340 },
      ),
    );
    const run =
      model.tables.search_runs[i] ??
      model.tables.search_runs[model.tables.search_runs.length - 1];
    if (run) {
      edges.push({
        id: `${run.id}-${source.id}`,
        source: run.id,
        target: source.id,
      });
    }
  });

  model.tables.evidence_units.forEach((ev, i) => {
    nodes.push(
      node(
        ev.evidence_id,
        {
          kind: "EvidenceUnit",
          label: "Evidence",
          subtitle: `${ev.relation} · ${ev.direction}`,
          access_level: ev.access_level,
          entityId: ev.evidence_id,
        },
        { x: 80 + i * 240, y: 500 },
      ),
    );
    if (ev.source_id) {
      edges.push({
        id: `${ev.source_id}-${ev.evidence_id}`,
        source: ev.source_id,
        target: ev.evidence_id,
      });
    } else if (claim) {
      edges.push({
        id: `${claim.id}-${ev.evidence_id}`,
        source: claim.id,
        target: ev.evidence_id,
      });
    }
  });

  const latestVerdict = model.tables.verdict_versions.at(-1);
  if (latestVerdict) {
    nodes.push(
      node(
        latestVerdict.id,
        {
          kind: "Verdict",
          label: "Verdict",
          subtitle: latestVerdict.verdict,
          verdict: latestVerdict.verdict,
          entityId: latestVerdict.id,
        },
        { x: 300, y: 660 },
      ),
    );
    for (const evidenceId of latestVerdict.evidence_ids) {
      edges.push({
        id: `${evidenceId}-${latestVerdict.id}`,
        source: evidenceId,
        target: latestVerdict.id,
        style: { strokeWidth: 2 },
      });
    }
  }

  return { nodes, edges };
}

export function isActiveStage(status: JobViewState): boolean {
  return (
    status === "submitting" ||
    status === "streaming" ||
    status === "complete" ||
    status === "degraded" ||
    status === "failed"
  );
}
