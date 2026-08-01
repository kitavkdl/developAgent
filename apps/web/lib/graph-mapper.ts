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
  const deltaDecision = model.cacheDecision === "DELTA";
  const claim =
    model.tables.claims[0] ??
    (model.status !== "idle" && model.query
      ? {
          id: "claim-1",
          text: model.query,
          created_at: "",
        }
      : undefined);
  const runCount = model.tables.search_runs.length;
  const sourceCount = Math.max(model.tables.sources.length, 1);
  const candidateCount = Math.max(model.tables.candidates.length, 1);

  if (claim) {
    const pulsing =
      isFocused(model, claim.id) &&
      (model.lastEventType === "claim.extracted" ||
        model.lastEventType === "claim.triaged" ||
        model.lastEventType === "cache.decision" ||
        model.lastEventType === "route.decided" ||
        model.lastEventType === "industry.classified");
    nodes.push(
      node(
        claim.id,
        {
          kind: "Claim",
          label: "Claim",
          subtitle: claim.text,
          entityId: claim.id,
          pulse: pulsing,
          emphasis: Boolean(model.cacheDecision || model.triage),
          cacheRing: model.cacheDecision,
          stale:
            deltaDecision &&
            model.status === "streaming" &&
            !model.deltaRefreshStarted,
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
          provider: run.provider,
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
          entityId: source.id,
          stale: reused && deltaDecision,
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
          stale: reused && deltaDecision,
          fresh: freshDelta,
          selected: isSelectedPath(selectedEntityId, run.id, source.id),
        }),
      );
    } else if (claim) {
      edges.push(
        edge(`${claim.id}-${source.id}`, claim.id, source.id, {
          stale: reused && deltaDecision,
          fresh: freshDelta,
          selected: isSelectedPath(selectedEntityId, claim.id, source.id),
        }),
      );
    }
  });

  model.tables.candidates.forEach((cand, i) => {
    const spread = Math.max(candidateCount - 1, 1);
    const x = 60 + (i * 500) / spread;
    const reused = model.reusedEntityIds.includes(cand.candidate_id);
    const freshDelta = model.freshEntityIds.includes(cand.candidate_id);
    nodes.push(
      node(
        cand.candidate_id,
        {
          kind: "Candidate",
          label: cand.passes_gate ? "Candidate ✓" : "Candidate",
          subtitle: cand.title ?? cand.candidate_id,
          entityId: cand.candidate_id,
          passesGate: cand.passes_gate,
          stale: reused && deltaDecision,
          reused,
          freshDelta,
          pulse: isFocused(model, cand.candidate_id),
          emphasis:
            cand.passes_gate ||
            freshDelta ||
            isFocused(model, cand.candidate_id),
        },
        { x, y: 480 },
      ),
    );
    if (cand.source_id) {
      edges.push(
        edge(
          `${cand.source_id}-${cand.candidate_id}`,
          cand.source_id,
          cand.candidate_id,
          {
            stale: reused && deltaDecision,
            fresh: freshDelta,
            selected: isSelectedPath(
              selectedEntityId,
              cand.source_id,
              cand.candidate_id,
            ),
          },
        ),
      );
    } else if (claim) {
      edges.push(
        edge(`${claim.id}-${cand.candidate_id}`, claim.id, cand.candidate_id, {
          stale: reused && deltaDecision,
          fresh: freshDelta,
          selected: isSelectedPath(
            selectedEntityId,
            claim.id,
            cand.candidate_id,
          ),
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
    const linkIds =
      latestVerdict.candidate_ids.length > 0
        ? latestVerdict.candidate_ids
        : claim
          ? [claim.id]
          : [];
    for (const id of linkIds) {
      const freshDelta = model.freshEntityIds.includes(id);
      const reused = model.reusedEntityIds.includes(id);
      edges.push(
        edge(`${id}-${latestVerdict.id}`, id, latestVerdict.id, {
          verdict: true,
          fresh: freshDelta,
          stale: reused && deltaDecision && !freshDelta,
          selected: isSelectedPath(selectedEntityId, id, latestVerdict.id),
        }),
      );
    }
  }

  if (selectedEntityId) {
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
