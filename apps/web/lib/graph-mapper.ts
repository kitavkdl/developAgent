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
    className: [
      data.pulse ? "rf-node--pulse" : "",
      data.emphasis ? "rf-node--emphasis" : "",
      data.stale || data.reused ? "rf-node--dim" : "",
      data.freshDelta ? "rf-node--fresh" : "",
    ]
      .filter(Boolean)
      .join(" "),
  };
}

function edge(
  id: string,
  source: string,
  target: string,
  opts: {
    animated?: boolean;
    verdict?: boolean;
    stale?: boolean;
    fresh?: boolean;
    selected?: boolean;
  } = {},
): Edge {
  const kind = opts.verdict
    ? "verdict"
    : opts.fresh
      ? "fresh"
      : opts.stale
        ? "stale"
        : "growth";

  return {
    id,
    source,
    target,
    type: "growth",
    animated: Boolean(opts.animated),
    className: [
      "growth-edge",
      `growth-edge--${kind}`,
      opts.selected ? "is-path" : "",
      opts.animated ? "is-live" : "",
    ]
      .filter(Boolean)
      .join(" "),
    style: {
      strokeWidth: opts.verdict ? 2.5 : opts.selected ? 2.25 : 1.5,
      stroke: opts.verdict
        ? "rgba(159, 217, 176, 0.85)"
        : opts.fresh
          ? "rgba(226, 181, 114, 0.9)"
          : opts.stale
            ? "rgba(232, 220, 196, 0.28)"
            : "rgba(232, 220, 196, 0.55)",
    },
    data: { kind },
  };
}

function isFocused(model: JobViewModel, id: string): boolean {
  return model.focusEntityIds.includes(id);
}

function isSelectedPath(
  selectedEntityId: string | null,
  a: string,
  b: string,
): boolean {
  return selectedEntityId === a || selectedEntityId === b;
}

function pickRunForSource(
  model: JobViewModel,
  index: number,
): { id: string; status: string } | null {
  const runs = model.tables.search_runs;
  if (!runs.length) return null;
  return runs[Math.min(index, runs.length - 1)] ?? null;
}

export function mapJobToGraph(
  model: JobViewModel,
  selectedEntityId: string | null = null,
): {
  nodes: Node[];
  edges: Edge[];
} {
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  const staleDecision = model.cacheDecision === "HIT_STALE";
  const claim = model.tables.claims[0];
  const runCount = model.tables.search_runs.length;
  const sourceCount = Math.max(model.tables.sources.length, 1);
  const evidenceCount = Math.max(model.tables.evidence_units.length, 1);

  if (claim) {
    const pulsing =
      isFocused(model, claim.id) &&
      (model.lastEventType === "claim.normalized" ||
        model.lastEventType === "cache.decision" ||
        model.lastEventType === "cache.candidate");
    nodes.push(
      node(
        claim.id,
        {
          kind: "Claim",
          label: "Claim",
          subtitle: claim.signature_summary,
          entityId: claim.id,
          pulse: pulsing,
          emphasis: Boolean(model.cacheDecision),
          cacheRing: model.cacheDecision,
          stale: staleDecision && model.status === "streaming" && !model.deltaRefreshStarted,
        },
        { x: 320, y: 24 },
      ),
    );
  }

  model.tables.search_runs.forEach((run, i) => {
    const spread = Math.max(runCount - 1, 1);
    const x = 120 + (i * 400) / spread;
    const pulsing =
      isFocused(model, run.id) || model.activeSearchRunId === run.id;
    nodes.push(
      node(
        run.id,
        {
          kind: "SearchRun",
          label: run.provider === "scholar" ? "Scholar" : "Web",
          subtitle: run.query || run.status,
          entityId: run.id,
          pulse: pulsing && run.status === "running",
          emphasis: pulsing,
        },
        { x, y: 168 },
      ),
    );
    if (claim) {
      edges.push(
        edge(`${claim.id}-${run.id}`, claim.id, run.id, {
          animated: run.status === "running",
          selected: isSelectedPath(selectedEntityId, claim.id, run.id),
        }),
      );
    }
  });

  model.tables.sources.forEach((source, i) => {
    const spread = Math.max(sourceCount - 1, 1);
    const x = 40 + (i * 520) / spread;
    const reused = model.reusedEntityIds.includes(source.id);
    const freshDelta = model.freshEntityIds.includes(source.id);
    nodes.push(
      node(
        source.id,
        {
          kind: "Source",
          label: "Source",
          subtitle: source.title,
          access_level: source.access_level,
          entityId: source.id,
          stale: reused && staleDecision,
          reused,
          freshDelta,
          pulse: isFocused(model, source.id),
          emphasis: freshDelta || isFocused(model, source.id),
        },
        { x, y: 320 },
      ),
    );

    const run = pickRunForSource(model, i);
    if (run) {
      edges.push(
        edge(`${run.id}-${source.id}`, run.id, source.id, {
          stale: reused && staleDecision,
          fresh: freshDelta,
          selected: isSelectedPath(selectedEntityId, run.id, source.id),
        }),
      );
    } else if (claim) {
      // HIT_FRESH / reuse-without-search: Claim → Source
      edges.push(
        edge(`${claim.id}-${source.id}`, claim.id, source.id, {
          stale: reused && staleDecision,
          fresh: freshDelta,
          selected: isSelectedPath(selectedEntityId, claim.id, source.id),
        }),
      );
    }
  });

  model.tables.evidence_units.forEach((ev, i) => {
    const spread = Math.max(evidenceCount - 1, 1);
    const x = 60 + (i * 500) / spread;
    const reused = model.reusedEntityIds.includes(ev.evidence_id);
    const freshDelta = model.freshEntityIds.includes(ev.evidence_id);
    nodes.push(
      node(
        ev.evidence_id,
        {
          kind: "EvidenceUnit",
          label: "Evidence",
          subtitle: `${ev.relation} · ${ev.direction}`,
          access_level: ev.access_level,
          entityId: ev.evidence_id,
          stale: reused && staleDecision,
          reused,
          freshDelta,
          pulse: isFocused(model, ev.evidence_id),
          emphasis: freshDelta || isFocused(model, ev.evidence_id),
        },
        { x, y: 480 },
      ),
    );
    if (ev.source_id) {
      edges.push(
        edge(`${ev.source_id}-${ev.evidence_id}`, ev.source_id, ev.evidence_id, {
          stale: reused && staleDecision,
          fresh: freshDelta,
          selected: isSelectedPath(
            selectedEntityId,
            ev.source_id,
            ev.evidence_id,
          ),
        }),
      );
    } else if (claim) {
      edges.push(
        edge(`${claim.id}-${ev.evidence_id}`, claim.id, ev.evidence_id, {
          stale: reused && staleDecision,
          fresh: freshDelta,
          selected: isSelectedPath(selectedEntityId, claim.id, ev.evidence_id),
        }),
      );
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
          pulse: isFocused(model, latestVerdict.id),
          emphasis: true,
        },
        { x: 320, y: 640 },
      ),
    );
    for (const evidenceId of latestVerdict.evidence_ids) {
      const freshDelta = model.freshEntityIds.includes(evidenceId);
      const reused = model.reusedEntityIds.includes(evidenceId);
      edges.push(
        edge(`${evidenceId}-${latestVerdict.id}`, evidenceId, latestVerdict.id, {
          verdict: true,
          fresh: freshDelta,
          stale: reused && staleDecision && !freshDelta,
          selected: isSelectedPath(
            selectedEntityId,
            evidenceId,
            latestVerdict.id,
          ),
        }),
      );
    }
  }

  // Citation path: selected evidence ↔ claim soft path already covered by adjacency.
  // Also emphasize edges when selected evidence is a citation.
  if (
    selectedEntityId &&
    model.citationEvidenceIds.includes(selectedEntityId) &&
    claim
  ) {
    const claimToEv = edges.find(
      (e) =>
        (e.source === claim.id && e.target === selectedEntityId) ||
        (e.source === selectedEntityId && e.target === claim.id),
    );
    if (!claimToEv) {
      // Walk Source path — mark edges touching selected evidence
      for (const e of edges) {
        if (e.source === selectedEntityId || e.target === selectedEntityId) {
          e.className = `${e.className ?? ""} is-path`.trim();
          e.style = {
            ...e.style,
            strokeWidth: 2.25,
            stroke: "rgba(196, 120, 43, 0.95)",
          };
        }
      }
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
