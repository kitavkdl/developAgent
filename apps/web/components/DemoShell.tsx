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

      {!active ? (
        <section className="hero">
          <p className="hero__brand">COUNTER</p>
          <h1 className="hero__title">Counter-evidence, made visible</h1>
          <p className="hero__lede">
            One claim in. Watch triage, cache routing, LINER search, and
            deterministic gates assemble a four-value verdict — on dummy memory
            for now.
          </p>
          <SearchBar busy={busy} onSubmit={submit} />
          <div className="hero__controls">
            <ScenarioSwitcher value={scenario} onChange={setScenario} />
            <PlaybackSpeedControl
              value={playbackSpeed}
              onChange={setPlaybackSpeed}
            />
          </div>
        </section>
      ) : (
        <div className="stage">
          <header className="stage__top">
            <div className="stage__brand-row">
              <button type="button" className="brand-mark" onClick={reset}>
                COUNTER
              </button>
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
              <span className="stage__status" data-status={model.status}>
                {model.status}
              </span>
            </div>
            <SearchBar
              compact
              busy={busy}
              initialQuery={model.query}
              onSubmit={submit}
            />
            <div className="stage__controls">
              <ScenarioSwitcher value={scenario} onChange={setScenario} />
              <PlaybackSpeedControl
                value={playbackSpeed}
                onChange={setPlaybackSpeed}
              />
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
      )}
    </div>
  );
}
