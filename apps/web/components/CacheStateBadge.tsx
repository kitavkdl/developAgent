import type { CacheDecision } from "@/types/domain";

const LABELS: Record<CacheDecision, string> = {
  HIT: "Cache hit",
  MISS: "Cache miss",
  DELTA: "Delta search",
  REVERIFY: "Reverify",
};

export function CacheStateBadge({
  decision,
  reusedCount,
}: {
  decision: CacheDecision | null;
  reusedCount?: number | null;
}) {
  if (!decision) return null;

  return (
    <span className="cache-badge" data-decision={decision}>
      {LABELS[decision]}
      {typeof reusedCount === "number" ? ` · ${reusedCount} reused` : null}
    </span>
  );
}
