"use client";

import { useMemo, useState } from "react";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  DATABASE_RELATIONS,
  DATABASE_TABLES,
  type DatabaseTableDefinition,
} from "@/lib/database-schema";
import styles from "@/app/database/database.module.css";

function SchemaTableNode({ data, selected }: NodeProps) {
  const table = data as unknown as DatabaseTableDefinition;

  return (
    <article
      className={`${styles.tableNode} ${selected ? styles.tableNodeSelected : ""}`}
      data-visibility={table.visibility}
    >
      <Handle type="target" position={Position.Left} />
      <div className={styles.tableNodeHeader}>
        <span className={styles.tableGlyph} aria-hidden="true">
          <i />
          <i />
          <i />
        </span>
        <strong>{table.label}</strong>
      </div>
      <span className={styles.visibilityBadge}>{table.visibility}</span>
      <p>{table.description}</p>
      <ul>
        {table.fields.map((field) => (
          <li key={field}>
            <code>{field}</code>
          </li>
        ))}
      </ul>
      <Handle type="source" position={Position.Right} />
    </article>
  );
}

const nodeTypes = { schemaTable: SchemaTableNode };

const edgeClassByKind = {
  ownership: styles.schemaEdgeOwnership,
  lineage: styles.schemaEdgeLineage,
  derivation: styles.schemaEdgeDerivation,
};

const schemaNodes: Node[] = DATABASE_TABLES.map((table) => ({
  id: table.id,
  type: "schemaTable",
  position: table.position,
  data: { ...table },
  draggable: false,
}));

const schemaEdges: Edge[] = DATABASE_RELATIONS.map((relation) => ({
  id: relation.id,
  source: relation.source,
  target: relation.target,
  label: relation.label,
  type: "smoothstep",
  markerEnd: { type: MarkerType.ArrowClosed },
  className: `${styles.schemaEdge} ${edgeClassByKind[relation.kind]}`,
  labelStyle: { fill: "#9baba3", fontSize: 11 },
  labelBgStyle: { fill: "#0b1714", fillOpacity: 0.92 },
}));

export function DatabaseSchemaExplorer() {
  const [selectedTableId, setSelectedTableId] = useState<string>("research_jobs");
  const selectedTable = useMemo(
    () => DATABASE_TABLES.find((table) => table.id === selectedTableId),
    [selectedTableId],
  );

  return (
    <section className={styles.explorer} aria-labelledby="schema-map-heading">
      <header className={styles.explorerHeader}>
        <div>
          <span className={styles.sectionIndex}>02 / Logical map</span>
          <h2 id="schema-map-heading">Persistence lineage</h2>
        </div>
        <div className={styles.legend} aria-label="Data visibility legend">
          <span data-visibility="shared-public">Shared public</span>
          <span data-visibility="tenant-private">Tenant private</span>
        </div>
      </header>

      <div className={styles.graphShell}>
        <ReactFlow
          nodes={schemaNodes}
          edges={schemaEdges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.12, maxZoom: 0.88 }}
          minZoom={0.3}
          maxZoom={1.15}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable
          onNodeClick={(_, node) => setSelectedTableId(node.id)}
          proOptions={{ hideAttribution: true }}
        >
          <Background gap={24} size={1} color="rgba(205, 222, 212, 0.1)" />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>

      <div className={styles.mobileList} aria-label="Database tables">
        {DATABASE_TABLES.map((table, index) => (
          <button
            key={table.id}
            type="button"
            className={selectedTableId === table.id ? styles.mobileCardActive : ""}
            onClick={() => setSelectedTableId(table.id)}
          >
            <span>{String(index + 1).padStart(2, "0")}</span>
            <strong>{table.label}</strong>
            <small>{table.visibility}</small>
            <p>{table.description}</p>
            <code>{table.fields.join(" · ")}</code>
          </button>
        ))}
      </div>

      {selectedTable ? (
        <footer className={styles.selectionSummary} aria-live="polite">
          <span>Selected table</span>
          <strong>{selectedTable.label}</strong>
          <p>{selectedTable.description}</p>
        </footer>
      ) : null}
    </section>
  );
}
