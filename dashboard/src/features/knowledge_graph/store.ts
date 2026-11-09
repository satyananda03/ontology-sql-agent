// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import MiniSearch from "minisearch";
import { create } from "zustand";
import type { RawEdge, RawGraph, RawNode } from "./types";

// Above this, building the search index costs more than searching saves.
const SEARCH_INDEX_LIMIT = 50_000;

export type SearchIndex = MiniSearch<{ id: string; label: string }>;

interface KnowledgeGraphState {
  rawGraph: RawGraph | null;
  selectedNode: string | null;
  selectedEdge: string | null;
  focusedNode: string | null;
  focusedEdge: string | null;
  /** True only when an explicit search result should move the camera. */
  moveToSelectedNode: boolean;
  searchIndex: SearchIndex | null;
  isLayoutRunning: boolean;
  /**
   * Bumped whenever `rawGraph` is replaced, so the viewer remounts Sigma on a
   * freshly built graph instead of mutating a live-bound one. Node drag does
   * NOT bump this: dragging only moves x/y on the existing instance.
   */
  dataVersion: number;
  setRawGraph: (graph: RawGraph) => void;
  setLayoutRunning: (running: boolean) => void;
  selectNode: (id: string | null, moveTo?: boolean) => void;
  selectEdge: (id: string | null) => void;
  focusNode: (id: string | null) => void;
  focusEdge: (id: string | null) => void;
  clearSelection: () => void;
  updateNodePosition: (nodeId: string, position: { x: number; y: number }) => void;
}

function createSearchIndex(rawGraph: RawGraph): SearchIndex | null {
  if (rawGraph.nodes.length > SEARCH_INDEX_LIMIT) return null;
  const index: SearchIndex = new MiniSearch({
    idField: "id",
    fields: ["label"],
    searchOptions: { prefix: true, fuzzy: 0.2 },
  });
  index.addAll(rawGraph.nodes.map(({ id, label }) => ({ id, label })));
  return index;
}

const NO_SELECTION = {
  selectedNode: null,
  selectedEdge: null,
  focusedNode: null,
  focusedEdge: null,
  moveToSelectedNode: false,
};

export const useKnowledgeGraphStore = create<KnowledgeGraphState>((set) => ({
  rawGraph: null,
  ...NO_SELECTION,
  searchIndex: null,
  isLayoutRunning: false,
  dataVersion: 0,
  setRawGraph: (rawGraph) =>
    set((state) => ({
      rawGraph,
      searchIndex: createSearchIndex(rawGraph),
      ...NO_SELECTION,
      dataVersion: state.dataVersion + 1,
    })),
  setLayoutRunning: (isLayoutRunning) => set({ isLayoutRunning }),
  selectNode: (selectedNode, moveToSelectedNode = false) =>
    set({ selectedNode, selectedEdge: null, moveToSelectedNode }),
  selectEdge: (selectedEdge) => set({ selectedEdge, selectedNode: null, moveToSelectedNode: false }),
  focusNode: (focusedNode) => set({ focusedNode }),
  focusEdge: (focusedEdge) => set({ focusedEdge }),
  clearSelection: () => set(NO_SELECTION),
  // Keeps a dragged position for the next rebuild. The live instance already
  // moved under the drag handler, so this must not bump dataVersion.
  updateNodePosition: (nodeId, position) =>
    set((state) => ({
      rawGraph: state.rawGraph && {
        ...state.rawGraph,
        nodes: state.rawGraph.nodes.map((node) => (node.id === nodeId ? { ...node, ...position } : node)),
      },
    })),
}));

export function selectedElement(
  rawGraph: RawGraph | null,
  nodeId: string | null,
  edgeId: string | null,
): { type: "node"; element: RawNode } | { type: "edge"; element: RawEdge } | null {
  if (!rawGraph) return null;
  if (nodeId) {
    const element = rawGraph.nodes.find((node) => node.id === nodeId);
    return element ? { type: "node", element } : null;
  }
  if (edgeId) {
    const element = rawGraph.edges.find((edge) => edge.id === edgeId);
    return element ? { type: "edge", element } : null;
  }
  return null;
}
