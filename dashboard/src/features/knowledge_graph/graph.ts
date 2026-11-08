// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

// Pure functions: API response -> RawGraph -> the graphology instance Sigma draws.
// Runtime imports stay relative, so the tests run without the `@` alias.

import { MultiUndirectedGraph } from "graphology";
import type { S } from "@/types";
import { EDGE_COLORS, resolveNodeColor } from "./graphColor";
import type { EdgeDisplayData, EdgeKind, NodeDisplayData, RawEdge, RawGraph, RawNode } from "./types";

export type SigmaGraph = MultiUndirectedGraph<NodeDisplayData, EdgeDisplayData>;

const MIN_NODE_SIZE = 4;
const MAX_NODE_SIZE = 20;
const MIN_EDGE_SIZE = 1;
const MAX_EDGE_SIZE = 2;
// Every node gets this border; the node-border program reads `borderColor`.
const NODE_BORDER_COLOR = "#000000";

/** The relationship type that marks a term link as an inferred join. */
const SEMANTIC_FK = "SEMANTIC_FK";

/** A deterministic starting position in 0..1, so a graph lays out the same way every time. */
export function hashPosition(id: string): { x: number; y: number } {
  let left = 0xdeadbeef ^ id.length;
  let right = 0x41c6ce57 ^ id.length;
  for (let index = 0; index < id.length; index += 1) {
    const char = id.charCodeAt(index);
    left = Math.imul(left ^ char, 2654435761);
    right = Math.imul(right ^ char, 1597334677);
  }
  return { x: (left >>> 0) / 4294967296, y: (right >>> 0) / 4294967296 };
}

type NodeInput = Omit<RawNode, "degree">;
type EdgeInput = Omit<RawEdge, "id">;

/** Drop duplicates and edges with a missing end, count degrees, and colour the groups. */
function buildRawGraph(nodeInputs: NodeInput[], edgeInputs: EdgeInput[]): RawGraph {
  const nodes = new Map<string, RawNode>();
  for (const node of nodeInputs) {
    if (!nodes.has(node.id)) nodes.set(node.id, { ...node, degree: 0 });
  }
  const edgesById = new Map<string, RawEdge>();
  for (const edge of edgeInputs) {
    const id = `${edge.source}|${edge.target}`;
    if (nodes.has(edge.source) && nodes.has(edge.target) && !edgesById.has(id)) edgesById.set(id, { ...edge, id });
  }
  const edges = [...edgesById.values()];
  for (const edge of edges) {
    nodes.get(edge.source)!.degree += 1;
    nodes.get(edge.target)!.degree += 1;
  }
  let groupColors = new Map<string, string>();
  for (const node of nodes.values()) groupColors = resolveNodeColor(node.group, groupColors).map;
  return { nodes: [...nodes.values()], edges, groupColors };
}

/** Terms as nodes, linked when they share a table; an inferred join gets its own colour. */
export function semanticGraphToRaw(graph: S["SemanticExplorationGraph"]): RawGraph {
  const nodes = (graph.nodes ?? []).map((term) => ({
    id: term.id,
    label: term.name || term.id,
    group: "term",
    properties: {
      Deskripsi: term.description,
      Sinonim: (term.synonyms ?? []).join(", "),
      "Atribut kolom": term.column_attributes_count,
      "Atribut SQL": term.sql_attributes_count,
    },
  }));
  const edges = (graph.links ?? []).map((link) => {
    const relationshipTypes = link.relationship_types ?? [];
    const kind: EdgeKind = relationshipTypes.includes(SEMANTIC_FK) ? "semanticFk" : "sharedTable";
    return {
      source: link.source,
      target: link.target,
      kind,
      weight: relationshipTypes.length,
      relationshipTypes,
      foreignKeys: [],
      queries: [],
    };
  });
  return buildRawGraph(nodes, edges);
}

/**
 * Tables as nodes, coloured by schema. Foreign-key edges always show; an edge
 * backed only by a shared SQL query shows when asked, because those queries
 * come from a `pg_stat_activity` snapshot and are hit and miss.
 */
export function dataGraphToRaw(
  graph: S["DataExplorationGraph"],
  { includeSqlEdges }: { includeSqlEdges: boolean },
): RawGraph {
  const nodes = (graph.nodes ?? []).map((table) => ({
    id: table.id,
    label: table.name || table.id,
    group: table.schema_name ?? "",
    properties: {
      Schema: table.schema_name,
      Jenis: table.table_type,
      Kolom: table.columns_count,
      Term: table.terms_count,
      "Query SQL": table.sql_count,
      Deskripsi: table.description,
    },
  }));
  const edges = (graph.links ?? [])
    .filter((link) => includeSqlEdges || link.via_foreign_key)
    .map((link) => {
      const kind: EdgeKind = link.via_foreign_key ? "foreignKey" : "sqlOnly";
      const foreignKeys = link.foreign_keys ?? [];
      const queries = link.queries ?? [];
      return {
        source: link.source,
        target: link.target,
        kind,
        weight: foreignKeys.length + queries.length,
        relationshipTypes: link.relationship_types ?? [],
        foreignKeys,
        queries,
      };
    });
  return buildRawGraph(nodes, edges);
}

/** `min..max` scaled by the square root of where *value* sits in its range. */
function scale(value: number, lowest: number, range: number, min: number, max: number): number {
  return range > 0 ? min + (max - min) * Math.sqrt((value - lowest) / range) : min;
}

/**
 * Build a brand-new, fully populated graphology instance from raw graph data.
 *
 * IMPORTANT: this always returns a fresh instance. Callers must not mutate a
 * Sigma-bound instance in place (clear + re-add) -- Sigma keeps internal render
 * caches (e.g. edge index buffers) that get corrupted by that pattern, causing
 * "edge can't be repaint" errors. Every new dataset must produce a new
 * instance that Sigma binds to once, fully built.
 */
export function sigmaGraphFromRaw(raw: RawGraph): SigmaGraph {
  const graph: SigmaGraph = new MultiUndirectedGraph();

  const degrees = raw.nodes.map((node) => node.degree);
  const minDegree = Math.min(...degrees);
  const degreeRange = Math.max(...degrees) - minDegree;
  for (const node of raw.nodes) {
    const position = hashPosition(node.id);
    const { color } = resolveNodeColor(node.group, raw.groupColors);
    graph.addNode(node.id, {
      x: node.x ?? position.x,
      y: node.y ?? position.y,
      label: node.label,
      color,
      labelColor: color,
      size: scale(node.degree, minDegree, degreeRange, MIN_NODE_SIZE, MAX_NODE_SIZE),
      borderColor: NODE_BORDER_COLOR,
    });
  }

  const weights = raw.edges.map((edge) => edge.weight);
  const minWeight = Math.min(...weights);
  const weightRange = Math.max(...weights) - minWeight;
  for (const edge of raw.edges) {
    graph.addEdgeWithKey(edge.id, edge.source, edge.target, {
      rawId: edge.id,
      originalWeight: edge.weight,
      size: scale(edge.weight, minWeight, weightRange, MIN_EDGE_SIZE, MAX_EDGE_SIZE),
      color: EDGE_COLORS[edge.kind],
    });
  }
  return graph;
}
