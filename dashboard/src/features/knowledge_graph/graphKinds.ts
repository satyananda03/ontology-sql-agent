// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import type { ComponentType } from "react";
import { ForeignKeyDetails, TermPathDetails } from "@/components/knowledge_graph/GraphDetails";
import { getDataGraph, getSemanticGraph } from "./api";
import { combinedGraphToRaw } from "./graph";
import type { EdgeKind, NodeKind, RawEdge, RawGraph } from "./types";

/** Terms and tables in one graph, from both endpoints at once. */
export async function loadGraph(databaseId: string): Promise<RawGraph> {
  const [semantic, data] = await Promise.all([getSemanticGraph(databaseId), getDataGraph(databaseId)]);
  return combinedGraphToRaw(semantic, data);
}

export interface NodeKindConfig {
  /** Legend name and the plain-words line under it. */
  label: string;
  hint: string;
  openLink: (nodeId: string) => { to: string; label: string };
}

export const NODE_KINDS: Record<NodeKind, NodeKindConfig> = {
  term: {
    label: "Term",
    hint: "konsep bisnis",
    openLink: (termId) => ({ to: `/terms/${termId}`, label: "Buka di Terms" }),
  },
  table: {
    label: "Tabel",
    hint: "tabel di database",
    openLink: (tableId) => ({ to: `/catalog?table=${tableId}`, label: "Buka di Katalog" }),
  },
};

/** Name and plain-words meaning of each edge kind, shown in the properties panel. */
export const EDGE_KINDS: Record<EdgeKind, { label: string; hint: string }> = {
  termTable: { label: "Term ↔ Tabel", hint: "term dibangun dari tabel ini" },
  sharedTable: { label: "Term ↔ Term", hint: "memakai tabel yang sama" },
  semanticFk: { label: "Join inferensi", hint: "terhubung lewat kolom yang mirip foreign key" },
  foreignKey: { label: "Foreign key", hint: "tabel saling mereferensi" },
  sqlOnly: { label: "Query SQL", hint: "dipakai bersama di query tersimpan" },
};

/** The drill-down for an edge, picked by what it connects: term-term has a path, table-table has keys. */
export function edgeDetails(edge: RawEdge, nodeKind: (id: string) => NodeKind | undefined): ComponentType<{ edge: RawEdge }> | null {
  const ends = [nodeKind(edge.source), nodeKind(edge.target)];
  if (ends.every((kind) => kind === "term")) return TermPathDetails;
  if (ends.every((kind) => kind === "table")) return ForeignKeyDetails;
  return null;
}
