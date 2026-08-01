"use client";

import { useEffect, useRef, useState } from "react";
import type { TableRows, TableTab } from "@/types/domain";

const TABS: { id: TableTab; label: string }[] = [
  { id: "claims", label: "claims" },
  { id: "candidates", label: "candidates" },
  { id: "sources", label: "sources" },
  { id: "verdict_versions", label: "verdict_versions" },
];

const EMPTY_FLASH_IDS = new Set<string>();

function useFlashIds(ids: string[]): Set<string> {
  const seen = useRef(new Set<string>());
  const [flashing, setFlashing] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (ids.length === 0) {
      seen.current.clear();
      return;
    }

    const newcomers = ids.filter((id) => !seen.current.has(id));
    if (!newcomers.length) return;
    for (const id of newcomers) seen.current.add(id);
    setFlashing((prev) => new Set([...prev, ...newcomers]));
    const t = setTimeout(() => {
      setFlashing((prev) => {
        const next = new Set(prev);
        for (const id of newcomers) next.delete(id);
        return next;
      });
    }, 700);
    return () => clearTimeout(t);
  }, [ids]);

  return ids.length === 0 ? EMPTY_FLASH_IDS : flashing;
}

export function SchemaTablePanel({
  tables,
  selectedEntityId,
  onSelect,
}: {
  tables: TableRows;
  selectedEntityId: string | null;
  onSelect: (id: string) => void;
}) {
  const [tab, setTab] = useState<TableTab>("candidates");
  const flashClaims = useFlashIds(tables.claims.map((r) => r.id));
  const flashCandidates = useFlashIds(
    tables.candidates.map((r) => r.candidate_id),
  );
  const flashSources = useFlashIds(tables.sources.map((r) => r.id));
  const flashVerdicts = useFlashIds(tables.verdict_versions.map((r) => r.id));

  return (
    <section className="panel table-panel">
      <header className="panel__header">
        <h2>Evidence memory</h2>
        <div className="table-tabs">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={tab === t.id ? "is-active" : undefined}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </header>
      <div className="table-scroll">
        <table>
          <thead>
            {tab === "claims" ? (
              <tr>
                <th>id</th>
                <th>text</th>
                <th>triage</th>
                <th>claim_type</th>
              </tr>
            ) : null}
            {tab === "candidates" ? (
              <tr>
                <th>candidate_id</th>
                <th>passes_gate</th>
                <th>published_at</th>
                <th>title</th>
              </tr>
            ) : null}
            {tab === "sources" ? (
              <tr>
                <th>id</th>
                <th>title</th>
                <th>published_at</th>
                <th>url</th>
              </tr>
            ) : null}
            {tab === "verdict_versions" ? (
              <tr>
                <th>id</th>
                <th>verdict</th>
                <th>query_count</th>
                <th>candidate_ids</th>
              </tr>
            ) : null}
          </thead>
          <tbody>
            {tab === "claims" &&
              tables.claims.map((row) => (
                <tr
                  key={row.id}
                  className={[
                    selectedEntityId === row.id ? "is-selected" : "",
                    flashClaims.has(row.id) ? "is-flash" : "",
                  ]
                    .filter(Boolean)
                    .join(" ") || undefined}
                  onClick={() => onSelect(row.id)}
                >
                  <td>{row.id}</td>
                  <td>{row.text}</td>
                  <td>{row.triage ?? "—"}</td>
                  <td>{row.claim_type ?? "—"}</td>
                </tr>
              ))}
            {tab === "candidates" &&
              tables.candidates.map((row) => (
                <tr
                  key={row.candidate_id}
                  className={[
                    selectedEntityId === row.candidate_id ? "is-selected" : "",
                    flashCandidates.has(row.candidate_id) ? "is-flash" : "",
                  ]
                    .filter(Boolean)
                    .join(" ") || undefined}
                  onClick={() => onSelect(row.candidate_id)}
                >
                  <td>{row.candidate_id}</td>
                  <td>{row.passes_gate ? "true" : "false"}</td>
                  <td>{row.published_at ?? "null"}</td>
                  <td>{row.title ?? "—"}</td>
                </tr>
              ))}
            {tab === "sources" &&
              tables.sources.map((row) => (
                <tr
                  key={row.id}
                  className={[
                    selectedEntityId === row.id ? "is-selected" : "",
                    flashSources.has(row.id) ? "is-flash" : "",
                  ]
                    .filter(Boolean)
                    .join(" ") || undefined}
                  onClick={() => onSelect(row.id)}
                >
                  <td>{row.id}</td>
                  <td>{row.title}</td>
                  <td>{row.published_at ?? "—"}</td>
                  <td>{row.url ?? "—"}</td>
                </tr>
              ))}
            {tab === "verdict_versions" &&
              tables.verdict_versions.map((row) => (
                <tr
                  key={row.id}
                  className={[
                    selectedEntityId === row.id ? "is-selected" : "",
                    flashVerdicts.has(row.id) ? "is-flash" : "",
                  ]
                    .filter(Boolean)
                    .join(" ") || undefined}
                  onClick={() => onSelect(row.id)}
                >
                  <td>{row.id}</td>
                  <td>{row.verdict}</td>
                  <td>{row.query_count}</td>
                  <td>{row.candidate_ids.join(", ") || "—"}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
