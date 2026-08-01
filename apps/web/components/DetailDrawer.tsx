import type { JobViewModel } from "@/lib/job-reducer";
import type { EvidenceUnitView } from "@/types/domain";

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

  const evidence = model.tables.evidence_units.find(
    (e: EvidenceUnitView) => e.evidence_id === selectedEntityId,
  );
  const source = model.tables.sources.find(
    (s: { id: string }) => s.id === selectedEntityId,
  );
  const claim = model.tables.claims.find(
    (c: { id: string }) => c.id === selectedEntityId,
  );
  const verdict = model.tables.verdict_versions.find(
    (v: { id: string }) => v.id === selectedEntityId,
  );

  return (
    <aside className="detail-drawer" aria-live="polite">
      <header>
        <h2>Detail</h2>
        <button type="button" onClick={onClose} aria-label="Close detail">
          Close
        </button>
      </header>

      {evidence ? (
        <dl>
          <dt>evidence_id</dt>
          <dd>{evidence.evidence_id}</dd>
          <dt>claim_id</dt>
          <dd>{evidence.claim_id}</dd>
          <dt>title</dt>
          <dd>{evidence.title ?? "—"}</dd>
          <dt>url</dt>
          <dd>
            {evidence.url ? (
              <a href={evidence.url} target="_blank" rel="noreferrer">
                {evidence.url}
              </a>
            ) : (
              "—"
            )}
          </dd>
          <dt>access_level</dt>
          <dd>
            <strong>{evidence.access_level}</strong>
          </dd>
          <dt>relation</dt>
          <dd>{evidence.relation}</dd>
          <dt>direction</dt>
          <dd>{evidence.direction}</dd>
          <dt>extracted_at</dt>
          <dd>{evidence.extracted_at}</dd>
          <dt>excerpt_or_summary</dt>
          <dd>{evidence.excerpt_or_summary}</dd>
        </dl>
      ) : null}

      {source && !evidence ? (
        <dl>
          <dt>source_id</dt>
          <dd>{source.id}</dd>
          <dt>title</dt>
          <dd>{source.title}</dd>
          <dt>access_level</dt>
          <dd>
            <strong>{source.access_level}</strong>
          </dd>
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
        </dl>
      ) : null}

      {claim ? (
        <dl>
          <dt>claim_id</dt>
          <dd>{claim.id}</dd>
          <dt>signature_summary</dt>
          <dd>{claim.signature_summary}</dd>
          <dt>created_at</dt>
          <dd>{claim.created_at}</dd>
        </dl>
      ) : null}

      {verdict ? (
        <dl>
          <dt>verdict</dt>
          <dd>{verdict.verdict}</dd>
          <dt>evidence_ids</dt>
          <dd>{verdict.evidence_ids.join(", ")}</dd>
          <dt>evaluated_at</dt>
          <dd>{verdict.evaluated_at}</dd>
        </dl>
      ) : null}

      {!evidence && !source && !claim && !verdict ? (
        <p className="detail-drawer__empty">No detail for {selectedEntityId}</p>
      ) : null}
    </aside>
  );
}
