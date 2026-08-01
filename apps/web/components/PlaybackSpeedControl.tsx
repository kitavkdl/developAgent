"use client";

import type { PlaybackSpeed } from "@/types/domain";

const OPTIONS: { id: PlaybackSpeed; label: string }[] = [
  { id: "slow", label: "Slow" },
  { id: "normal", label: "Normal" },
  { id: "fast", label: "Fast" },
];

export function PlaybackSpeedControl({
  value,
  onChange,
}: {
  value: PlaybackSpeed;
  onChange: (speed: PlaybackSpeed) => void;
}) {
  return (
    <div className="playback-speed" aria-label="Demo playback speed">
      <span className="playback-speed__label">Pace</span>
      <div className="playback-speed__options">
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
