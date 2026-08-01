import type { JobViewModel } from "@/lib/job-reducer";
import type { ResearchEventType } from "@/types/events";

const PROGRESS_COPY: Partial<
  Record<ResearchEventType, { title: string; detail: string }>
> = {
  "job.created": {
    title: "Preparing the research run",
    detail: "Your claim is entering the evidence pipeline.",
  },
  "intake.completed": {
    title: "Reading the claim",
    detail: "The intake is complete. Claim extraction is next.",
  },
  "claim.extracted": {
    title: "Structuring the claim",
    detail: "COUNTER is isolating the statement that can be tested.",
  },
  "claim.triaged": {
    title: "Testing falsifiability",
    detail: "The claim is being routed to the right evidence workflow.",
  },
  "route.decided": {
    title: "Choosing an evidence route",
    detail: "The search scope is being narrowed before retrieval.",
  },
  "industry.classified": {
    title: "Matching the evidence domain",
    detail: "Relevant memory and search context are being selected.",
  },
  "cache.decision": {
    title: "Checking evidence memory",
    detail: "COUNTER is deciding what can be reused and what needs review.",
  },
  "tool.call": {
    title: "Searching for counter-evidence",
    detail: "Public sources are being queried for applicable evidence.",
  },
  "tool.result": {
    title: "Reading the search results",
    detail: "Potential sources are being prepared for applicability checks.",
  },
  "candidate.evaluated": {
    title: "Testing applicability",
    detail: "Scope, metric, timeframe, and target must all match.",
  },
  "verdict.assembled": {
    title: "Assembling the answer",
    detail: "The verdict and supporting summary are almost ready.",
  },
};

const DEFAULT_PROGRESS = {
  title: "The answer will take shape here",
  detail: "COUNTER is starting the research pipeline.",
};

export function AnswerPreview({
  status,
  lastEventType,
  verdict,
  summary,
  errorMessage,
}: Pick<
  JobViewModel,
  "status" | "lastEventType" | "verdict" | "summary" | "errorMessage"
>) {
  const hasAnswer = Boolean(verdict && summary);
  const progress =
    (lastEventType ? PROGRESS_COPY[lastEventType] : undefined) ??
    DEFAULT_PROGRESS;

  return (
    <section
      className="answer-preview"
      data-state={hasAnswer ? "answer" : status}
      aria-labelledby="answer-preview-heading"
    >
      <div className="answer-preview__eyebrow">
        <span aria-hidden="true" />
        {hasAnswer
          ? status === "degraded"
            ? "Partial answer"
            : "Answer ready"
          : status === "failed"
            ? "Research stopped"
            : "Answer preview"}
      </div>

      {hasAnswer ? (
        <div className="answer-preview__result" aria-live="polite">
          <span className="answer-preview__verdict" data-verdict={verdict}>
            {verdict}
          </span>
          <h2 id="answer-preview-heading">What the evidence says</h2>
          <p>{summary}</p>
          {status === "degraded" ? (
            <small>{errorMessage || "Completed with partial evidence."}</small>
          ) : null}
        </div>
      ) : status === "failed" ? (
        <div className="answer-preview__result is-error" role="alert">
          <h2 id="answer-preview-heading">We couldn&apos;t finish this run</h2>
          <p>{errorMessage || "The research pipeline stopped unexpectedly."}</p>
        </div>
      ) : (
        <div className="answer-preview__progress">
          <h2 id="answer-preview-heading">{progress.title}</h2>
          <p>{progress.detail}</p>
          <span className="answer-preview__activity" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
        </div>
      )}
    </section>
  );
}
