// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

// Ported from frontend_references/src/components/knowledge_graph/KnowledgeGraphHeader.tsx:
// the node search as it was; the workspace toggle became the Semantik | Data tabs.

import { useEffect, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { GRAPH_KINDS } from "@/features/knowledge_graph/graphKinds";
import { useKnowledgeGraphStore, type SearchIndex } from "@/features/knowledge_graph/store";
import type { GraphKind, RawNode } from "@/features/knowledge_graph/types";

const DEFAULT_RESULTS = 15;
const MAX_RESULTS = 20;

export function KnowledgeGraphHeader() {
  const kind = useKnowledgeGraphStore((state) => state.kind);
  const setKind = useKnowledgeGraphStore((state) => state.setKind);
  const includeSqlEdges = useKnowledgeGraphStore((state) => state.includeSqlEdges);
  const setIncludeSqlEdges = useKnowledgeGraphStore((state) => state.setIncludeSqlEdges);

  return (
    <header className="pointer-events-none absolute left-0 right-0 top-0 z-20 flex items-center justify-between px-6 py-5 sm:px-8">
      <div className="pointer-events-auto flex flex-wrap items-center gap-4">
        <NodeSearch />
        {GRAPH_KINDS[kind].hasSqlEdgeToggle && (
          <label className="flex cursor-pointer items-center gap-2 font-mono text-xs text-neutral-300 hover:text-white">
            <input
              type="checkbox"
              checked={includeSqlEdges}
              onChange={(event) => setIncludeSqlEdges(event.target.checked)}
              className="accent-[#E72C0E]"
            />
            Relasi query SQL
          </label>
        )}
      </div>

      <div className="pointer-events-auto flex h-10 items-center overflow-hidden rounded-sm border border-[#333333] bg-[#1C1C1C] text-xs">
        {(Object.keys(GRAPH_KINDS) as GraphKind[]).map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setKind(tab)}
            className={`flex h-full cursor-pointer items-center justify-center px-5 font-medium transition-colors ${
              tab === kind ? "bg-[#E72C0E] font-semibold text-white" : "text-neutral-400 hover:text-white"
            }`}
          >
            {GRAPH_KINDS[tab].tab}
          </button>
        ))}
      </div>
    </header>
  );
}

function NodeSearch() {
  const rawGraph = useKnowledgeGraphStore((state) => state.rawGraph);
  const searchIndex = useKnowledgeGraphStore((state) => state.searchIndex);
  const selectNode = useKnowledgeGraphStore((state) => state.selectNode);
  const focusNode = useKnowledgeGraphStore((state) => state.focusNode);
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const closeOnOutsideClick = (event: MouseEvent) => {
      if (!searchRef.current?.contains(event.target as Node)) setIsOpen(false);
    };
    document.addEventListener("mousedown", closeOnOutsideClick);
    return () => document.removeEventListener("mousedown", closeOnOutsideClick);
  }, []);

  const results = searchNodes(rawGraph?.nodes ?? [], query, searchIndex);

  const choose = (nodeId: string) => {
    focusNode(null);
    selectNode(nodeId, true);
    setIsOpen(false);
  };

  return (
    <div ref={searchRef} className="relative">
      <div className="flex h-10 w-48 items-center gap-2 rounded-sm border border-[#333333] bg-[#1C1C1C] px-3 text-xs transition-colors focus-within:border-[#E72C0E] sm:w-60">
        <Search className="h-3.5 w-3.5 shrink-0 text-neutral-400" />
        <input
          type="text"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && results[0]) {
              event.preventDefault();
              choose(results[0].id);
            }
            if (event.key === "Escape") setIsOpen(false);
          }}
          placeholder="Cari node…"
          aria-label="Cari node"
          className="w-full bg-transparent font-mono text-xs text-white placeholder-neutral-500 outline-none"
        />
        {query && (
          <button type="button" onClick={() => setQuery("")} className="text-neutral-500 hover:text-white" title="Hapus">
            <X className="h-3 w-3" />
          </button>
        )}
      </div>

      {isOpen && (
        <div className="absolute left-0 z-30 mt-1.5 max-h-72 w-64 overflow-y-auto rounded-sm border border-[#333333] bg-[#1C1C1C] py-1 font-mono text-xs shadow-2xl">
          {results.length > 0 ? (
            results.map((node) => (
              <button
                key={node.id}
                type="button"
                onMouseEnter={() => focusNode(node.id)}
                onClick={() => choose(node.id)}
                className="block w-full truncate px-3.5 py-2 text-left text-neutral-300 transition-colors hover:bg-[#2A2A2A] hover:text-white"
              >
                {node.label}
              </button>
            ))
          ) : (
            <div className="px-3.5 py-3 text-center text-xs text-neutral-500">Tidak ada node yang cocok</div>
          )}
        </div>
      )}
    </div>
  );
}

/** Index hits first, then plain substring matches the fuzzy index missed. */
function searchNodes(
  nodes: RawNode[],
  query: string,
  searchIndex: SearchIndex | null,
): RawNode[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return nodes.slice(0, DEFAULT_RESULTS);
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const hits = searchIndex ? searchIndex.search(normalized).map((result) => String(result.id)) : [];
  const hitSet = new Set(hits);
  const substring = nodes
    .filter((node) => !hitSet.has(node.id) && node.label.toLowerCase().includes(normalized))
    .map((node) => node.id);
  return [...hits, ...substring]
    .slice(0, MAX_RESULTS)
    .map((id) => byId.get(id))
    .filter((node): node is RawNode => Boolean(node));
}
