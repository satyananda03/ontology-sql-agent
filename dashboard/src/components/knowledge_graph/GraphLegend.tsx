// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

// Ported from frontend_references/src/components/knowledge_graph/GraphLegend.tsx,
// with edge kinds added below the node groups.

import { EDGE_COLORS } from "@/features/knowledge_graph/graphColor";
import { GRAPH_KINDS } from "@/features/knowledge_graph/graphKinds";
import { useKnowledgeGraphStore } from "@/features/knowledge_graph/store";

export function GraphLegend() {
  const rawGraph = useKnowledgeGraphStore((state) => state.rawGraph);
  const config = GRAPH_KINDS[useKnowledgeGraphStore((state) => state.kind)];
  if (!rawGraph?.groupColors.size) return null;

  // Only the edge kinds this graph actually has, so a hidden toggle leaves no orphan row.
  const edgeKinds = new Set(rawGraph.edges.map((edge) => edge.kind));
  const edgeRows = config.edgeLegend.filter((row) => edgeKinds.has(row.kind));

  return (
    <aside className="max-h-80 w-52 overflow-auto rounded-xl border border-[#2E2E2E] bg-[#161616]/95 p-3 font-mono text-xs text-neutral-200 shadow-2xl backdrop-blur-md">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-neutral-100">Legenda</h3>
      <div className="flex flex-col gap-1.5">
        {[...rawGraph.groupColors].map(([group, color]) => (
          <div className="flex items-center gap-2" key={group}>
            <span className="size-3 shrink-0 rounded-full" style={{ backgroundColor: color }} />
            <span className="truncate text-[11px]" style={{ color }} title={group}>
              {config.groupLabel(group)}
            </span>
          </div>
        ))}
        {edgeRows.map(({ kind, label }) => (
          <div className="flex items-center gap-2" key={kind}>
            <span className="h-0.5 w-3 shrink-0 rounded-full" style={{ backgroundColor: EDGE_COLORS[kind] }} />
            <span className="truncate text-[11px] text-neutral-300">{label}</span>
          </div>
        ))}
      </div>
    </aside>
  );
}
