import type { VerdictEnum } from "@/types/domain";

export function VerdictAnswerPanel({
  verdict,
  answer,
  reasonCodes,
  citationIds,
  onCite,
}: {
  verdict: VerdictEnum | null;
  answer: string;
  reasonCodes: string[];
  citationIds: string[];
  onCite?: (evidenceId: string) => void;
}) {
  if (!verdict && !answer) return null;

  return (
    <section className="panel verdict-panel">
      <header className="panel__header">
        <h2>Verdict</h2>
        {verdict ? (
          <span className="verdict-chip" data-verdict={verdict}>
            {verdict}
          </span>
        ) : null}
      </header>
      {reasonCodes.length > 0 ? (
        <p className="verdict-reasons">{reasonCodes.join(" · ")}</p>
      ) : null}
      <p className="verdict-answer">{answer || "Synthesizing answer…"}</p>
      {citationIds.length > 0 ? (
        <div className="verdict-cites">
          {citationIds.map((id) => (
            <button key={id} type="button" onClick={() => onCite?.(id)}>
              {id}
            </button>
          ))}
        </div>
      ) : null}
    </section>
  );
}
