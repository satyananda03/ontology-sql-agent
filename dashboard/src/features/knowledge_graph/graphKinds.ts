// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import type { ComponentType } from "react";
import {
  ForeignKeyDetails,
  TableDetails,
  TermDetails,
  TermPathDetails,
} from "@/components/knowledge_graph/GraphDetails";
import { getDataGraph, getSemanticGraph } from "./api";
import { dataGraphToRaw, semanticGraphToRaw } from "./graph";
import type { EdgeKind, GraphKind, RawEdge, RawGraph } from "./types";

export interface GraphLoadOptions {
  includeSqlEdges: boolean;
}

/** Everything that differs between the two tabs, so the components stay kind-agnostic. */
export interface GraphKindConfig {
  tab: string;
  load: (databaseId: string, options: GraphLoadOptions) => Promise<RawGraph>;
  emptyMessage: string;
  groupLabel: (group: string) => string;
  edgeLegend: { kind: EdgeKind; label: string }[];
  /** Whether the header offers the toggle for edges backed only by a shared SQL query. */
  hasSqlEdgeToggle: boolean;
  openLink: (nodeId: string) => { to: string; label: string };
  /** Drill-down shown in the properties panel for the selected node or edge. */
  NodeDetails: ComponentType<{ nodeId: string }>;
  EdgeDetails: ComponentType<{ edge: RawEdge }>;
}

export const GRAPH_KINDS: Record<GraphKind, GraphKindConfig> = {
  semantic: {
    tab: "Semantik",
    load: async (databaseId) => semanticGraphToRaw(await getSemanticGraph(databaseId)),
    emptyMessage: "Belum ada term. Jalankan kompilasi di Pengaturan → Operasi.",
    groupLabel: () => "Term",
    edgeLegend: [
      { kind: "sharedTable", label: "Berbagi tabel" },
      { kind: "semanticFk", label: "Join hasil inferensi" },
    ],
    hasSqlEdgeToggle: false,
    openLink: (termId) => ({ to: `/terms/${termId}`, label: "Buka di Terms" }),
    NodeDetails: TermDetails,
    EdgeDetails: TermPathDetails,
  },
  data: {
    tab: "Data",
    load: async (databaseId, { includeSqlEdges }) =>
      dataGraphToRaw(await getDataGraph(databaseId), { includeSqlEdges }),
    emptyMessage: "Belum ada tabel. Jalankan Ingest ulang di Pengaturan → Operasi.",
    groupLabel: (schema) => schema,
    edgeLegend: [
      { kind: "foreignKey", label: "Foreign key" },
      { kind: "sqlOnly", label: "Query SQL bersama" },
    ],
    hasSqlEdgeToggle: true,
    openLink: (tableId) => ({ to: `/catalog?table=${tableId}`, label: "Buka di Katalog" }),
    NodeDetails: TableDetails,
    EdgeDetails: ForeignKeyDetails,
  },
};
