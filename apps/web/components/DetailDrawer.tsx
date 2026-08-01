import type { JobViewModel } from "@/lib/job-reducer";
import type { CandidateView } from "@/types/domain";

export function DetailDrawer({
  model,
  selectedEntityId,
  onClose,
}: {
  model: JobViewModel;
  selectedEntityId: string | null;
  onClose: () => void;
}) {
  if (!selectedEntityId) return null;

  const candidate = model.tables.candidates.find(
    (e: CandidateView) => e.candidate_id === selectedEntityId,
  );
  const source = model.tables.sources.find((s) => s.id === selectedEntityId);
  const claim = model.tables.claims.find((c) => c.id === selectedEntityId);
  const verdict = model.tables.verdict_versions.find(
    (v) => v.id === selectedEntityId,
  );
  const run = model.tables.search_runs.find((r) => r.id === selectedEntityId);

  return (
    <aside className="detail-drawer" aria-live="polite">
      <header>
        <h2>Detail</h2>
        <button type="button" onClick={onClose} aria-label="Close detail">
          Close
        </button>
      </header>

      {candidate ? (
        <dl>
          <dt>candidate_id</dt>
          <dd>{candidate.candidate_id}</dd>
          <dt>title</dt>
          <dd>{candidate.title ?? "—"}</dd>
          <dt>url</dt>
          <dd>
            {candidate.url ? (
              <a href={candidate.url} target="_blank" rel="noreferrer">
                {candidate.url}
              </a>
            ) : (
              "—"
            )}
          </dd>
          <dt>published_at</dt>
          <dd>{candidate.published_at ?? "null (timeframe not inferred)"}</dd>
          <dt>passes_gate</dt>
          <dd>{candidate.passes_gate ? "true" : "false"}</dd>
          <dt>applicability_check</dt>
          <dd>
            <ul className="check-list">
              {Object.entries(candidate.applicability_check).map(([k, v]) => (
                <li key={k} data-ok={v}>
                  {k}: {String(v)}
                </li>
              ))}
            </ul>
          </dd>
          <dt>excerpt</dt>
          <dd>{candidate.excerpt_or_summary}</dd>
        </dl>
      ) : null}

      {source && !candidate ? (
        <dl>
          <dt>source_id</dt>
          <dd>{source.id}</dd>
          <dt>title</dt>
          <dd>{source.title}</dd>
          <dt>url</dt>
          <dd>
            {source.url ? (
              <a href={source.url} target="_blank" rel="noreferrer">
                {source.url}
              </a>
            ) : (
              "—"
            )}
          </dd>
          <dt>published_at</dt>
          <dd>{source.published_at ?? "—"}</dd>
        </dl>
      ) : null}

      {claim ? (
        <dl>
          <dt>claim_id</dt>
          <dd>{claim.id}</dd>
          <dt>text</dt>
          <dd>{claim.text}</dd>
          <dt>triage</dt>
          <dd>{claim.triage ?? "—"}</dd>
          <dt>claim_type</dt>
          <dd>{claim.claim_type ?? "—"}</dd>
        </dl>
      ) : null}

      {run ? (
        <dl>
          <dt>search_run_id</dt>
          <dd>{run.id}</dd>
          <dt>provider</dt>
          <dd>{run.provider}</dd>
          <dt>query</dt>
          <dd>{run.query || "—"}</dd>
          <dt>status</dt>
          <dd>{run.status}</dd>
        </dl>
      ) : null}

      {verdict ? (
        <dl>
          <dt>verdict</dt>
          <dd>{verdict.verdict}</dd>
          <dt>query_count</dt>
          <dd>{verdict.query_count}</dd>
          <dt>candidate_ids</dt>
          <dd>{verdict.candidate_ids.join(", ") || "—"}</dd>
          <dt>summary</dt>
          <dd>{verdict.summary}</dd>
        </dl>
      ) : null}
    </aside>
  );
}
