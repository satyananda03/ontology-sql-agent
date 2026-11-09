// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

// What each node colour means, in plain words, with how many there are.

import { NODE_COLORS } from "@/features/knowledge_graph/graphColor";
import { NODE_KINDS } from "@/features/knowledge_graph/graphKinds";
import { useKnowledgeGraphStore } from "@/features/knowledge_graph/store";
import type { NodeKind } from "@/features/knowledge_graph/types";

export function GraphLegend() {
  const rawGraph = useKnowledgeGraphStore((state) => state.rawGraph);
  if (!rawGraph?.nodes.length) return null;

  const counts = new Map<NodeKind, number>();
  for (const { kind } of rawGraph.nodes) counts.set(kind, (counts.get(kind) ?? 0) + 1);

  return (
    <aside className="w-56 rounded-xl border border-[#2E2E2E] bg-[#161616]/95 p-3 font-mono text-xs text-neutral-200 shadow-2xl backdrop-blur-md">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-neutral-100">Legenda</h3>
      <div className="flex flex-col gap-1.5">
        {(Object.keys(NODE_KINDS) as NodeKind[]).map((kind) => (
          <div key={kind} className="flex items-center gap-2">
            <span className="size-3 shrink-0 rounded-full" style={{ backgroundColor: NODE_COLORS[kind] }} />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[11px]" style={{ color: NODE_COLORS[kind] }}>
                {NODE_KINDS[kind].label}
              </span>
              <span className="block truncate text-[10px] text-neutral-500">{NODE_KINDS[kind].hint}</span>
            </span>
            <span className="shrink-0 text-[10px] text-neutral-400">{counts.get(kind) ?? 0}</span>
          </div>
        ))}
      </div>
      <p className="mt-2 border-t border-[#2A2A2A] pt-2 text-[10px] text-neutral-500">Ukuran node = jumlah relasinya.</p>
    </aside>
  );
}
