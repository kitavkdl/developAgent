import type { VerdictEnum } from "@/types/domain";

const VERDICT_HINT: Partial<Record<VerdictEnum, string>> = {
  NOT_REFUTED:
    "이 결과는 주장이 사실임을 뜻하지 않습니다. 실행한 쿼리에서 반례를 찾지 못했을 뿐입니다.",
  PUFFERY: "검증 대상이 아닌 주관적 과장입니다. 검색 tool_call은 0건입니다.",
  PUBLIC_SUBSTANTIATION_NOT_FOUND:
    "실증이 필요한 유형인데 공개 근거를 확인하지 못했습니다.",
};

export function VerdictAnswerPanel({
  verdict,
  summary,
  reasonCodes,
  queryCount,
  citationIds,
  onCite,
}: {
  verdict: VerdictEnum | null;
  summary: string;
  reasonCodes: string[];
  queryCount: number;
  citationIds: string[];
  onCite?: (candidateId: string) => void;
}) {
  if (!verdict && !summary) return null;

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
      {typeof queryCount === "number" && verdict && verdict !== "PUFFERY" ? (
        <p className="verdict-queries">Queries executed · {queryCount}</p>
      ) : null}
      {reasonCodes.length > 0 ? (
        <p className="verdict-reasons">{reasonCodes.join(" · ")}</p>
      ) : null}
      <p className="verdict-answer">{summary || "Assembling verdict…"}</p>
      {verdict && VERDICT_HINT[verdict] ? (
        <p className="verdict-hint">{VERDICT_HINT[verdict]}</p>
      ) : null}
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
