"use client";

import { useEffect, useMemo } from "react";
import {
  Background,
  Controls,
  Handle,
  Position,
  ReactFlow,
  type NodeProps,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { GraphNodeData } from "@/types/domain";
import type { JobViewModel } from "@/lib/job-reducer";
import { mapJobToGraph } from "@/lib/graph-mapper";

function EvidenceNode(props: NodeProps) {
  const data = props.data as GraphNodeData;
  const selected = props.selected;
  return (
    <div
      className={`graph-node kind-${data.kind} ${data.stale ? "is-stale" : ""} ${
        selected ? "is-selected" : ""
      }`}
    >
      <Handle type="target" position={Position.Top} />
      <span className="graph-node__kind">{data.kind}</span>
      <strong>{data.label}</strong>
      {data.subtitle ? <p>{data.subtitle}</p> : null}
      {data.access_level ? (
        <em className="graph-node__access">{data.access_level}</em>
      ) : null}
      {data.verdict ? (
        <em className="graph-node__verdict" data-verdict={data.verdict}>
          {data.verdict}
        </em>
      ) : null}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

const nodeTypes = { evidence: EvidenceNode };

export function EvidenceGraph({
  model,
  selectedEntityId,
  onSelect,
}: {
  model: JobViewModel;
  selectedEntityId: string | null;
  onSelect: (id: string) => void;
}) {
  const mapped = useMemo(() => mapJobToGraph(model), [model]);
  const [nodes, setNodes, onNodesChange] = useNodesState(mapped.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(mapped.edges);

  useEffect(() => {
    setNodes(
      mapped.nodes.map((n) => ({
        ...n,
        selected: n.id === selectedEntityId,
      })),
    );
    setEdges(mapped.edges);
  }, [mapped, selectedEntityId, setNodes, setEdges]);

  return (
    <div className="evidence-graph">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        proOptions={{ hideAttribution: true }}
        onNodeClick={(_, n) =>
          onSelect(String((n.data as GraphNodeData).entityId))
        }
        minZoom={0.4}
        maxZoom={1.4}
      >
        <Background gap={22} size={1} color="rgba(232, 220, 196, 0.12)" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
