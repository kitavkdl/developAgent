"use client";

import type { DemoScenarioId } from "@/types/domain";

const OPTIONS: { id: DemoScenarioId; label: string }[] = [
  { id: "miss", label: "MISS" },
  { id: "fresh", label: "HIT_FRESH" },
  { id: "stale", label: "HIT_STALE" },
  { id: "seed", label: "SEED_ONLY" },
];

export function ScenarioSwitcher({
  value,
  onChange,
}: {
  value: DemoScenarioId;
  onChange: (id: DemoScenarioId) => void;
}) {
  return (
    <div className="scenario-switcher" aria-label="Demo scenario">
      <span className="scenario-switcher__label">Scenario</span>
      <div className="scenario-switcher__options">
        {OPTIONS.map((opt) => (
          <button
            key={opt.id}
            type="button"
            className={value === opt.id ? "is-active" : undefined}
            onClick={() => onChange(opt.id)}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}
