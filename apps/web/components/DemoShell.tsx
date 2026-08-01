"use client";

import { AgentTracePanel } from "@/components/AgentTracePanel";
import { CacheStateBadge } from "@/components/CacheStateBadge";
import { DetailDrawer } from "@/components/DetailDrawer";
import { EvidenceGraph } from "@/components/EvidenceGraph";
import { PlaybackSpeedControl } from "@/components/PlaybackSpeedControl";
import { ScenarioSwitcher } from "@/components/ScenarioSwitcher";
import { SchemaTablePanel } from "@/components/SchemaTablePanel";
import { SearchBar } from "@/components/SearchBar";
import { VerdictAnswerPanel } from "@/components/VerdictAnswerPanel";
import { isActiveStage } from "@/lib/graph-mapper";
import { useDemoOrchestrator } from "@/lib/use-demo-orchestrator";

export function DemoShell() {
  const {
    model,
    scenario,
    setScenario,
    playbackSpeed,
    setPlaybackSpeed,
    selectedEntityId,
    setSelectedEntityId,
    submit,
    reset,
  } = useDemoOrchestrator();

  const active = isActiveStage(model.status);
  const busy = model.status === "submitting" || model.status === "streaming";

  return (
    <div className={`demo-shell ${active ? "demo-shell--active" : ""}`}>
      <div className="demo-atmosphere" aria-hidden />

      <main className="workspace-shell">
        <section className="input-pane" aria-labelledby="counter-heading">
          <div className="input-pane__content">
            <button
              type="button"
              className="hero__brand"
              onClick={reset}
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
            <SearchBar
              compact={active}
              busy={busy}
              initialQuery={model.query}
              onSubmit={submit}
            />
            <div className="hero__controls">
              <ScenarioSwitcher value={scenario} onChange={setScenario} />
              <PlaybackSpeedControl
                value={playbackSpeed}
                onChange={setPlaybackSpeed}
              />
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
                <EvidenceGraph
                  model={model}
                  selectedEntityId={selectedEntityId}
                  onSelect={setSelectedEntityId}
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
