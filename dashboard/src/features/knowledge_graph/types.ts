// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import type { Attributes } from "graphology-types";
import type { S } from "@/types";

/** Which layer the viewer draws: terms (semantic) or tables (data). */
export type GraphKind = "semantic" | "data";

/** How two nodes are connected; picks the edge colour and its legend row. */
export type EdgeKind = "foreignKey" | "sqlOnly" | "semanticFk" | "sharedTable";

/** One row of the properties panel; empty values are left out when shown. */
export type NodeProperties = Record<string, string | number | null | undefined>;

export interface RawNode {
  id: string;
  label: string;
  /** Colour group: the schema of a table, "term" for a term. */
  group: string;
  properties: NodeProperties;
  degree: number;
  x?: number;
  y?: number;
}

export interface RawEdge {
  id: string;
  source: string;
  target: string;
  kind: EdgeKind;
  weight: number;
  relationshipTypes: string[];
  /** Data layer only: the key columns and stored queries behind the edge. */
  foreignKeys: S["ForeignKeyRef"][];
  queries: string[];
}

export interface RawGraph {
  nodes: RawNode[];
  edges: RawEdge[];
  /** Colour per node group, in first-seen order: the legend's rows. */
  groupColors: Map<string, string>;
}

export interface NodeDisplayData extends Attributes {
  x: number;
  y: number;
  label: string;
  color: string;
  labelColor?: string;
  size: number;
  borderColor: string;
  highlighted?: boolean;
}

export interface EdgeDisplayData extends Attributes {
  rawId: string;
  originalWeight: number;
  size: number;
  hidden?: boolean;
  color?: string;
}
