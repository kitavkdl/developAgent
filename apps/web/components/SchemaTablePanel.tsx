"use client";

import { useState } from "react";
import type { TableRows, TableTab } from "@/types/domain";

const TABS: { id: TableTab; label: string }[] = [
  { id: "claims", label: "claims" },
  { id: "evidence_units", label: "evidence_units" },
  { id: "sources", label: "sources" },
  { id: "verdict_versions", label: "verdict_versions" },
];

export function SchemaTablePanel({
  tables,
  selectedEntityId,
  onSelect,
}: {
  tables: TableRows;
  selectedEntityId: string | null;
  onSelect: (id: string) => void;
}) {
  const [tab, setTab] = useState<TableTab>("evidence_units");

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
                <th>signature_summary</th>
                <th>created_at</th>
              </tr>
            ) : null}
            {tab === "evidence_units" ? (
              <tr>
                <th>evidence_id</th>
                <th>access_level</th>
                <th>relation</th>
                <th>direction</th>
                <th>title</th>
              </tr>
            ) : null}
            {tab === "sources" ? (
              <tr>
                <th>id</th>
                <th>title</th>
                <th>access_level</th>
                <th>url</th>
              </tr>
            ) : null}
            {tab === "verdict_versions" ? (
              <tr>
                <th>id</th>
                <th>verdict</th>
                <th>evidence_ids</th>
                <th>evaluated_at</th>
              </tr>
            ) : null}
          </thead>
          <tbody>
            {tab === "claims" &&
              tables.claims.map((row) => (
                <tr
                  key={row.id}
                  className={selectedEntityId === row.id ? "is-selected" : undefined}
                  onClick={() => onSelect(row.id)}
                >
                  <td>{row.id}</td>
                  <td>{row.signature_summary}</td>
                  <td>{row.created_at}</td>
                </tr>
              ))}
            {tab === "evidence_units" &&
              tables.evidence_units.map((row) => (
                <tr
                  key={row.evidence_id}
                  className={
                    selectedEntityId === row.evidence_id ? "is-selected" : undefined
                  }
                  onClick={() => onSelect(row.evidence_id)}
                >
                  <td>{row.evidence_id}</td>
                  <td>{row.access_level}</td>
                  <td>{row.relation}</td>
                  <td>{row.direction}</td>
                  <td>{row.title ?? "—"}</td>
                </tr>
              ))}
            {tab === "sources" &&
              tables.sources.map((row) => (
                <tr
                  key={row.id}
                  className={selectedEntityId === row.id ? "is-selected" : undefined}
                  onClick={() => onSelect(row.id)}
                >
                  <td>{row.id}</td>
                  <td>{row.title}</td>
                  <td>{row.access_level}</td>
                  <td>{row.url ?? "—"}</td>
                </tr>
              ))}
            {tab === "verdict_versions" &&
              tables.verdict_versions.map((row) => (
                <tr
                  key={row.id}
                  className={selectedEntityId === row.id ? "is-selected" : undefined}
                  onClick={() => onSelect(row.id)}
                >
                  <td>{row.id}</td>
                  <td>{row.verdict}</td>
                  <td>{row.evidence_ids.join(", ")}</td>
                  <td>{row.evaluated_at}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
