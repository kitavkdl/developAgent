import type { TraceLine } from "@/types/domain";

export function AgentTracePanel({ traces }: { traces: TraceLine[] }) {
  return (
    <section className="panel trace-panel">
      <header className="panel__header">
        <h2>Agent trace</h2>
        <span>{traces.length} events</span>
      </header>
      <ol className="trace-list">
        {traces.length === 0 ? (
          <li className="trace-list__empty">Waiting for tool stream…</li>
        ) : (
          traces.map((line) => (
            <li key={line.id} data-kind={line.kind}>
              {line.agent_label ? (
                <span className="trace-agent">{line.agent_label}</span>
              ) : (
                <span className="trace-agent">System</span>
              )}
              <code>{line.summary}</code>
            </li>
          ))
        )}
      </ol>
    </section>
  );
}
