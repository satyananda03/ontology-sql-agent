// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

// Ported from frontend_references/src/components/knowledge_graph/GraphProperties.tsx,
// read-only: editing, merge and undo are gone, and the drill-down plus a link
// to the editing page come from GRAPH_KINDS.

import { useMemo, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { X } from "lucide-react";
import { GRAPH_KINDS, type GraphKindConfig } from "@/features/knowledge_graph/graphKinds";
import { selectedElement, useKnowledgeGraphStore } from "@/features/knowledge_graph/store";
import type { RawEdge, RawGraph, RawNode } from "@/features/knowledge_graph/types";

export function GraphProperties() {
  const rawGraph = useKnowledgeGraphStore((state) => state.rawGraph);
  const config = GRAPH_KINDS[useKnowledgeGraphStore((state) => state.kind)];
  const selectedNode = useKnowledgeGraphStore((state) => state.selectedNode);
  const selectedEdge = useKnowledgeGraphStore((state) => state.selectedEdge);
  const focusedNode = useKnowledgeGraphStore((state) => state.focusedNode);
  const focusedEdge = useKnowledgeGraphStore((state) => state.focusedEdge);
  // A hovered node or edge takes over the panel from the selected one.
  const activeNode = focusedNode ?? selectedNode;
  const activeEdge = focusedNode ? null : (focusedEdge ?? selectedEdge);
  const element = useMemo(() => selectedElement(rawGraph, activeNode, activeEdge), [rawGraph, activeNode, activeEdge]);
  if (!element || !rawGraph) return null;

  // The drill-down fetches follow the selection only: the panel also follows
  // every hover, and fetching on each one would flood the API.
  const showDetails = !focusedNode && !focusedEdge;
  return element.type === "node" ? (
    <NodePanel node={element.element} graph={rawGraph} config={config} showDetails={showDetails} />
  ) : (
    <EdgePanel edge={element.element} graph={rawGraph} config={config} showDetails={showDetails} />
  );
}

interface PanelProps {
  graph: RawGraph;
  config: GraphKindConfig;
  showDetails: boolean;
}

function NodePanel({ node, graph, config, showDetails }: PanelProps & { node: RawNode }) {
  const { NodeDetails } = config;
  const link = config.openLink(node.id);
  const neighbours = new Set(
    graph.edges
      .filter((edge) => edge.source === node.id || edge.target === node.id)
      .map((edge) => (edge.source === node.id ? edge.target : edge.source)),
  );

  return (
    <Panel title="Node" titleClass="text-[#00E5FF]">
      <div className="mb-4 space-y-2">
        <InfoRow label="Nama">{node.label}</InfoRow>
        <InfoRow label="Relasi">{node.degree}</InfoRow>
      </div>

      <div className="mb-4">
        <h4 className="mb-2.5 text-xs font-bold uppercase tracking-wider text-[#FFD600]">Properti</h4>
        <div className="max-h-48 space-y-2 overflow-y-auto pr-1">
          {Object.entries(node.properties)
            .filter(([, value]) => value !== null && value !== undefined && value !== "")
            .map(([name, value]) => (
              <div key={name} className="grid grid-cols-[90px_1fr] gap-2 border-b border-[#222222] py-1 last:border-0">
                <span className="shrink-0 truncate text-neutral-400" title={name}>
                  {name}
                </span>
                <span className="break-words text-[11px] leading-relaxed text-white">{value}</span>
              </div>
            ))}
        </div>
      </div>

      {showDetails && <NodeDetails nodeId={node.id} />}

      {neighbours.size > 0 && (
        <div className="mb-4">
          <h4 className="mb-2 text-xs font-bold tracking-wide text-[#00E676]">Relasi dalam graf</h4>
          <div className="max-h-52 space-y-1 overflow-y-auto pr-1">
            {[...neighbours].map((id) => (
              <button
                key={id}
                type="button"
                onClick={() => useKnowledgeGraphStore.getState().selectNode(id, true)}
                className="group flex w-full cursor-pointer items-center rounded border border-[#2A2A2A] bg-[#1C1C1C] px-2.5 py-1.5 text-left transition-colors hover:bg-[#252525]"
              >
                <span className="truncate text-[11px] text-neutral-300 group-hover:text-white">{nodeLabel(graph, id)}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <Link
        to={link.to}
        className="block rounded bg-[#E72C0E] px-3 py-2 text-center text-xs font-semibold text-white transition-colors hover:bg-[#c82509]"
      >
        {link.label} →
      </Link>
    </Panel>
  );
}

function EdgePanel({ edge, graph, config, showDetails }: PanelProps & { edge: RawEdge }) {
  const { EdgeDetails } = config;
  return (
    <Panel title="Relasi" titleClass="text-violet-400">
      <div className="mb-4 space-y-2">
        <InfoRow label="Dari">{nodeLabel(graph, edge.source)}</InfoRow>
        <InfoRow label="Ke">{nodeLabel(graph, edge.target)}</InfoRow>
        <InfoRow label="Jenis">{edge.relationshipTypes.join(", ")}</InfoRow>
      </div>
      {showDetails && <EdgeDetails edge={edge} />}
    </Panel>
  );
}

function Panel({ title, titleClass, children }: { title: string; titleClass: string; children: ReactNode }) {
  return (
    <aside className="absolute right-8 top-20 z-30 max-h-[calc(100%-110px)] w-80 overflow-y-auto rounded-xl border border-[#2A2A2A] bg-[#141414]/95 p-5 font-mono text-xs text-[#E0E0E0] shadow-2xl backdrop-blur-md md:w-88">
      <div className="mb-3 flex items-center justify-between border-b border-[#2A2A2A] pb-3">
        <h3 className={`text-sm font-bold tracking-wide ${titleClass}`}>{title}</h3>
        <button
          type="button"
          onClick={() => useKnowledgeGraphStore.getState().clearSelection()}
          title="Tutup"
          className="rounded p-1 text-neutral-400 transition-colors hover:bg-neutral-800 hover:text-white"
        >
          <X size={15} />
        </button>
      </div>
      {children}
    </aside>
  );
}

function InfoRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[80px_1fr] gap-2">
      <span className="text-neutral-400">{label}</span>
      <span className="break-words font-medium text-white">{children}</span>
    </div>
  );
}

const nodeLabel = (graph: RawGraph, id: string): string => graph.nodes.find((node) => node.id === id)?.label ?? id;
