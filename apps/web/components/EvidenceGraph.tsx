"use client";

import { useEffect, useMemo, useRef } from "react";
import {
  Background,
  BaseEdge,
  Controls,
  Handle,
  Position,
  ReactFlow,
  ReactFlowProvider,
  getBezierPath,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Edge,
  type EdgeProps,
  type Node,
  type NodeProps,
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
      className={`graph-node kind-${data.kind} ${data.stale || data.reused ? "is-stale" : ""} ${
        data.freshDelta ? "is-fresh" : ""
      } ${data.pulse ? "is-pulse" : ""} ${data.emphasis ? "is-emphasis" : ""} ${
        selected ? "is-selected" : ""
      } ${data.cacheRing ? "has-cache-ring" : ""}`}
      data-cache={data.cacheRing ?? undefined}
    >
      <Handle type="target" position={Position.Top} />
      {data.cacheRing ? (
        <span className="graph-node__cache-ring" data-decision={data.cacheRing}>
          {data.cacheRing}
        </span>
      ) : null}
      <span className="graph-node__kind">{data.kind}</span>
      <strong>{data.label}</strong>
      {data.subtitle ? <p>{data.subtitle}</p> : null}
      {data.provider ? (
        <em className="graph-node__access">liner · {data.provider}</em>
      ) : null}
      {typeof data.passesGate === "boolean" ? (
        <em className="graph-node__access">
          gate · {data.passesGate ? "pass" : "fail"}
        </em>
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

function GrowthEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style,
  markerEnd,
}: EdgeProps) {
  const [path] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });

  return (
    <BaseEdge
      id={id}
      path={path}
      markerEnd={markerEnd}
      style={style}
      className="growth-edge-path"
    />
  );
}

const nodeTypes = { evidence: EvidenceNode };
const edgeTypes = { growth: GrowthEdge };

function withNodeEntrance(prevIds: Set<string>, items: Node[]): Node[] {
  return items.map((item) => {
    if (prevIds.has(item.id)) return item;
    return {
      ...item,
      className: `${item.className ?? ""} is-entering`.trim(),
    };
  });
}

function withEdgeEntrance(prevIds: Set<string>, items: Edge[]): Edge[] {
  return items.map((item) => {
    if (prevIds.has(item.id)) return item;
    return {
      ...item,
      className: `${item.className ?? ""} is-drawing`.trim(),
    };
  });
}

function GraphCanvas({
  model,
  selectedEntityId,
  onSelect,
}: {
  model: JobViewModel;
  selectedEntityId: string | null;
  onSelect: (id: string) => void;
}) {
  const mapped = useMemo(
    () => mapJobToGraph(model, selectedEntityId),
    [model, selectedEntityId],
  );
  const structureKey = useMemo(
    () =>
      `${mapped.nodes.map((n) => n.id).join("|")}::${mapped.edges.map((e) => e.id).join("|")}`,
    [mapped.nodes, mapped.edges],
  );
  const [nodes, setNodes, onNodesChange] = useNodesState(mapped.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(mapped.edges);
  const knownNodeIds = useRef(new Set<string>());
  const knownEdgeIds = useRef(new Set<string>());
  const prevJobId = useRef<string | null | undefined>(undefined);
  const fitTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { fitView, setCenter, getNode } = useReactFlow();

  useEffect(() => {
    if (model.jobId !== prevJobId.current) {
      knownNodeIds.current = new Set();
      knownEdgeIds.current = new Set();
      prevJobId.current = model.jobId;
    }

    const nextNodes = withNodeEntrance(knownNodeIds.current, mapped.nodes);
    const nextEdges = withEdgeEntrance(knownEdgeIds.current, mapped.edges);

    const grew =
      mapped.nodes.some((n) => !knownNodeIds.current.has(n.id)) ||
      mapped.edges.some((e) => !knownEdgeIds.current.has(e.id));

    for (const n of mapped.nodes) knownNodeIds.current.add(n.id);
    for (const e of mapped.edges) knownEdgeIds.current.add(e.id);

    setNodes(
      nextNodes.map((n) => ({
        ...n,
        selected: n.id === selectedEntityId,
      })),
    );
    setEdges(nextEdges);

    if (!grew) return;

    if (fitTimer.current) clearTimeout(fitTimer.current);
    fitTimer.current = setTimeout(() => {
      void fitView({ padding: 0.22, duration: 320, maxZoom: 1.15 });
    }, 180);

    return () => {
      if (fitTimer.current) clearTimeout(fitTimer.current);
    };
  }, [
    mapped,
    structureKey,
    model.jobId,
    selectedEntityId,
    setNodes,
    setEdges,
    fitView,
  ]);

  useEffect(() => {
    if (model.growthComplete) {
      const t = setTimeout(() => {
        void fitView({ padding: 0.28, duration: 480, maxZoom: 1.05 });
      }, 120);
      return () => clearTimeout(t);
    }
  }, [model.growthComplete, fitView]);

  useEffect(() => {
    if (!selectedEntityId) return;
    const n = getNode(selectedEntityId);
    if (!n) return;
    const w = n.measured?.width ?? 160;
    const h = n.measured?.height ?? 80;
    void setCenter(n.position.x + w / 2, n.position.y + h / 2, {
      zoom: 1.05,
      duration: 380,
    });
  }, [selectedEntityId, getNode, setCenter, nodes.length]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      fitView
      fitViewOptions={{ padding: 0.22 }}
      proOptions={{ hideAttribution: true }}
      onNodeClick={(_, n) =>
        onSelect(String((n.data as GraphNodeData).entityId))
      }
      minZoom={0.35}
      maxZoom={1.4}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable
    >
      <Background gap={22} size={1} color="rgba(232, 220, 196, 0.12)" />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}

export function EvidenceGraph(props: {
  model: JobViewModel;
  selectedEntityId: string | null;
  onSelect: (id: string) => void;
  claimMorphing?: boolean;
}) {
  const { claimMorphing = false, ...canvasProps } = props;

  return (
    <div
      className={`evidence-graph ${
        claimMorphing
          ? "is-claim-morphing"
          : "is-claim-transition-source"
      }`}
    >
      <ReactFlowProvider>
        <GraphCanvas {...canvasProps} />
      </ReactFlowProvider>
    </div>
  );
}
