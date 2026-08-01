"use client";

import { useCallback, useState } from "react";
import { flushSync } from "react-dom";
import { AgentTracePanel } from "@/components/AgentTracePanel";
import { CacheStateBadge } from "@/components/CacheStateBadge";
import { DetailDrawer } from "@/components/DetailDrawer";
import { EvidenceGraph } from "@/components/EvidenceGraph";
import { ScenarioSwitcher } from "@/components/ScenarioSwitcher";
import { SchemaTablePanel } from "@/components/SchemaTablePanel";
import { SearchBar } from "@/components/SearchBar";
import { VerdictAnswerPanel } from "@/components/VerdictAnswerPanel";
import { isActiveStage } from "@/lib/graph-mapper";
import { useDemoOrchestrator } from "@/lib/use-demo-orchestrator";

function runClaimViewTransition(update: () => void, onFinished?: () => void) {
  const scrollPosition = { x: window.scrollX, y: window.scrollY };
  const restoreScroll = () => {
    window.scrollTo(scrollPosition.x, scrollPosition.y);
  };
  const reducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)",
  ).matches;

  if (
    reducedMotion ||
    typeof document.startViewTransition !== "function"
  ) {
    flushSync(update);
    onFinished?.();
    restoreScroll();
    return;
  }

  document.documentElement.dataset.claimTransition = "active";

  try {
    const transition = document.startViewTransition(() => {
      flushSync(update);
      restoreScroll();
    });

    void transition.finished
      .finally(() => {
        delete document.documentElement.dataset.claimTransition;
        onFinished?.();
        requestAnimationFrame(restoreScroll);
      })
      .catch(() => undefined);
  } catch {
    delete document.documentElement.dataset.claimTransition;
    flushSync(update);
    onFinished?.();
    restoreScroll();
  }
}

export function DemoShell() {
  const {
    model,
    scenario,
    setScenario,
    selectedEntityId,
    setSelectedEntityId,
    submit,
    reset,
  } = useDemoOrchestrator();
  const [claimMorphQuery, setClaimMorphQuery] = useState<string | null>(null);

  const active = isActiveStage(model.status);

  const handleSubmit = useCallback(
    (query: string) => {
      const trimmed = query.trim();
      if (!trimmed) return;

      runClaimViewTransition(
        () => {
          setClaimMorphQuery(trimmed);
          void submit(trimmed);
        },
        () => setClaimMorphQuery(null),
      );
    },
    [submit],
  );

  const handleReset = useCallback(() => {
    runClaimViewTransition(reset);
  }, [reset]);

  return (
    <div className={`demo-shell ${active ? "demo-shell--active" : ""}`}>
      <div className="demo-atmosphere" aria-hidden />

      <main className="workspace-shell">
        <section className="input-pane" aria-labelledby="counter-heading">
          <div className="input-pane__content">
            <button
              type="button"
              className="hero__brand"
              onClick={handleReset}
              disabled={!active}
              aria-label={active ? "Reset research workspace" : undefined}
            >
              COUNTER
            </button>
            <div className="input-pane__intro">
              <h1 id="counter-heading" className="hero__title">
                Counter-evidence, made visible
              </h1>
              <p className="hero__lede">
                One claim in. Watch triage, cache routing, LINER search, and
                deterministic gates assemble a four-value verdict — on dummy
                memory for now.
              </p>
            </div>
            {!active ? <SearchBar onSubmit={handleSubmit} /> : null}
            <div className="hero__controls">
              <ScenarioSwitcher value={scenario} onChange={setScenario} />
            </div>
          </div>
        </section>

        <section
          className="workspace-pane"
          aria-label="Research pipeline workspace"
          aria-hidden={!active}
          inert={!active}
        >
          <div className="stage">
            <header className="stage__top">
              <div className="stage__brand-row">
                <CacheStateBadge
                  decision={model.cacheDecision}
                  reusedCount={model.reusedCandidateCount}
                />
                {model.route ? (
                  <span className="route-chip" data-route={model.route}>
                    {model.route}
                  </span>
                ) : null}
                {model.industryLabel ? (
                  <span
                    className={`industry-chip ${model.industryIsNew ? "is-new" : ""}`}
                  >
                    {model.industryLabel}
                    {model.industryIsNew ? " · new" : ""}
                  </span>
                ) : null}
                <span
                  className="stage__status"
                  data-status={model.status}
                  aria-live="polite"
                >
                  {model.status}
                </span>
              </div>
            </header>

            <div className="stage__main">
              <div className="stage__graph-wrap">
                {claimMorphQuery ? (
                  <div
                    className="claim-morph-target graph-node kind-Claim"
                    aria-hidden="true"
                  >
                    <span className="graph-node__kind">Claim</span>
                    <strong>Claim</strong>
                    <p>{claimMorphQuery}</p>
                  </div>
                ) : null}
                <EvidenceGraph
                  key={active ? "active" : "idle"}
                  model={model}
                  selectedEntityId={selectedEntityId}
                  onSelect={setSelectedEntityId}
                  claimMorphing={Boolean(claimMorphQuery)}
                />
              </div>
              <div className="stage__side">
                <AgentTracePanel
                  traces={model.traces}
                  activeTraceId={model.activeTraceId}
                  focusEntityIds={model.focusEntityIds}
                />
                <VerdictAnswerPanel
                  verdict={model.verdict}
                  summary={model.summary}
                  reasonCodes={model.reasonCodes}
                  queryCount={model.queryCount}
                  citationIds={model.citationCandidateIds}
                  onCite={setSelectedEntityId}
                />
              </div>
            </div>

            <SchemaTablePanel
              tables={model.tables}
              selectedEntityId={selectedEntityId}
              onSelect={setSelectedEntityId}
            />

            <DetailDrawer
              model={model}
              selectedEntityId={selectedEntityId}
              onClose={() => setSelectedEntityId(null)}
            />

            {model.errorMessage ? (
              <div className="error-banner" role="alert">
                {model.errorMessage}
              </div>
            ) : null}
          </div>
        </section>
      </main>
    </div>
  );
}
