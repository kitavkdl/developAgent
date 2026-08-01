"use client";

import { FormEvent, useState } from "react";

export function SearchBar({
  compact,
  busy,
  initialQuery = "",
  onSubmit,
}: {
  compact?: boolean;
  busy?: boolean;
  initialQuery?: string;
  onSubmit: (query: string) => void;
}) {
  const [query, setQuery] = useState(initialQuery);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    onSubmit(query);
  }

  return (
    <form
      className={`search-bar ${compact ? "search-bar--compact" : ""}`}
      onSubmit={handleSubmit}
    >
      <label className="sr-only" htmlFor="claim-query">
        Claim or question
      </label>
      <input
        id="claim-query"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Enter an ad claim to counter-check…"
        autoComplete="off"
        disabled={busy}
      />
      <button type="submit" disabled={busy || !query.trim()}>
        {busy ? "Running…" : "Research"}
      </button>
    </form>
  );
}
