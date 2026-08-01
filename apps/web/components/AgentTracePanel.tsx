"use client";

import { useEffect, useRef } from "react";
import type { TraceLine } from "@/types/domain";

export function AgentTracePanel({
  traces,
  activeTraceId,
  focusEntityIds,
}: {
  traces: TraceLine[];
  activeTraceId?: string | null;
  focusEntityIds?: string[];
}) {
  const listRef = useRef<HTMLOListElement>(null);
  const focus = focusEntityIds ?? [];

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    const active = el.querySelector<HTMLElement>("li.is-active");
    if (!active) return;

    const listRect = el.getBoundingClientRect();
    const activeRect = active.getBoundingClientRect();
    let scrollDelta = 0;

    if (activeRect.top < listRect.top) {
      scrollDelta = activeRect.top - listRect.top;
    } else if (activeRect.bottom > listRect.bottom) {
      scrollDelta = activeRect.bottom - listRect.bottom;
    }

    if (scrollDelta !== 0) {
      el.scrollTo({
        top: el.scrollTop + scrollDelta,
        behavior: "smooth",
      });
    }
  }, [activeTraceId, traces.length]);

  return (
    <section className="panel trace-panel">
      <header className="panel__header">
        <h2>Agent trace</h2>
        <span>{traces.length} events</span>
      </header>
      <ol className="trace-list" ref={listRef}>
        {traces.length === 0 ? (
          <li className="trace-list__empty">Waiting for pipeline stream…</li>
        ) : (
          traces.map((line) => {
            const relatedHot =
              Boolean(line.relatedEntityId) &&
              focus.includes(line.relatedEntityId!);
            const active = line.id === activeTraceId || relatedHot;
            return (
              <li
                key={line.id}
                data-kind={line.kind}
                data-provider={line.provider}
                className={active ? "is-active" : undefined}
              >
                <span className="trace-meta">
                  {line.agent_label ? (
                    <span className="trace-agent">{line.agent_label}</span>
                  ) : (
                    <span className="trace-agent">System</span>
                  )}
                  {line.provider ? (
                    <span className="trace-provider" data-provider={line.provider}>
                      {line.provider}
                    </span>
                  ) : null}
                </span>
                <code>{line.summary}</code>
              </li>
            );
          })
        )}
      </ol>
    </section>
  );
}
