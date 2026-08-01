import type { CacheDecision } from "@/types/domain";

const LABELS: Record<CacheDecision, string> = {
  HIT_FRESH: "Cache fresh",
  HIT_STALE: "Cache stale",
  SEED_ONLY: "Seed only",
  MISS: "Cache miss",
  INVALID: "Invalidated",
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
