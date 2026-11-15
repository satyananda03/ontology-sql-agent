// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { queryOptions } from "@tanstack/react-query";
import type { ComponentType } from "react";
import { ForeignKeyDetails, TermPathDetails } from "@/components/knowledge_graph/GraphDetails";
import type { S } from "@/types";
import { getDataGraph, getSemanticGraph, getSqlAttributes } from "./api";
import type { EdgeKind, NodeKind, RawEdge, RawNode } from "./types";

/** What the graph is built from. Kept apart so the SQL attribute filter rebuilds without refetching. */
export interface GraphSources {
  semantic: S["SemanticExplorationGraph"];
  data: S["DataExplorationGraph"];
  sqlAttributes: S["SqlAttribute"][];
}

/** Terms, tables and SQL attributes, from all three endpoints at once. */
export async function loadGraph(databaseId: string): Promise<GraphSources> {
  const [semantic, data, sqlAttributes] = await Promise.all([
    getSemanticGraph(databaseId),
    getDataGraph(databaseId),
    getSqlAttributes(),
  ]);
  return { semantic, data, sqlAttributes };
}

export interface NodeKindConfig {
  /** Legend name and the plain-words line under it. */
  label: string;
  hint: string;
  openLink: (node: RawNode) => { to: string; label: string };
}

export const NODE_KINDS: Record<NodeKind, NodeKindConfig> = {
  term: {
    label: "Term",
    hint: "konsep bisnis",
    openLink: (node) => ({ to: `/terms/${node.id}`, label: "Buka di Business Terms" }),
  },
  table: {
    label: "Tabel",
    hint: "tabel di database",
    openLink: (node) => ({ to: `/catalog?table=${node.id}`, label: "Buka di Katalog" }),
  },
  sqlAttribute: {
    label: "Atribut SQL",
    hint: "rumus atau filter bisnis",
    // Edited on its term's page; there is no page of its own.
    openLink: (node) => ({ to: `/terms/${node.termId}`, label: "Buka term-nya di Business Terms" }),
  },
};

/** Name and plain-words meaning of each edge kind, shown in the properties panel. */
export const EDGE_KINDS: Record<EdgeKind, { label: string; hint: string }> = {
  termTable: { label: "Term ↔ Tabel", hint: "term dibangun dari tabel ini" },
  sharedTable: { label: "Term ↔ Term", hint: "memakai tabel yang sama" },
  semanticFk: { label: "Join inferensi", hint: "terhubung lewat kolom yang mirip foreign key" },
  foreignKey: { label: "Foreign key", hint: "tabel saling mereferensi" },
  sqlOnly: { label: "Query SQL", hint: "dipakai bersama di query tersimpan" },
  termSqlAttribute: { label: "Term ↔ Atribut SQL", hint: "rumus yang ditetapkan untuk term ini" },
  sqlAttributeTable: { label: "Atribut SQL ↔ Tabel", hint: "rumus ini juga memakai tabel ini" },
};

/** The drill-down for an edge, picked by what it connects: term-term has a path, table-table has keys. */
export function edgeDetails(edge: RawEdge, nodeKind: (id: string) => NodeKind | undefined): ComponentType<{ edge: RawEdge }> | null {
  const ends = [nodeKind(edge.source), nodeKind(edge.target)];
  if (ends.every((kind) => kind === "term")) return TermPathDetails;
  if (ends.every((kind) => kind === "table")) return ForeignKeyDetails;
  return null;
}

export const graphQuery = (databaseId: string) =>
  queryOptions({ queryKey: ["knowledge-graph", "graph", databaseId], queryFn: () => loadGraph(databaseId) });
