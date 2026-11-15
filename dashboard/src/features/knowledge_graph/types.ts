// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import type { Attributes } from "graphology-types";
import type { S } from "@/types";

/** What a node is: a business term, a database table or a SQL attribute. Picks its colour and legend row. */
export type NodeKind = "term" | "table" | "sqlAttribute";

/** How two nodes are connected; picks the edge colour and its legend row. */
export type EdgeKind =
  | "termTable"
  | "sharedTable"
  | "semanticFk"
  | "foreignKey"
  | "sqlOnly"
  | "termSqlAttribute"
  | "sqlAttributeTable";

/** Which SQL attributes the graph shows: none, only the user-made ones, or every one. */
export type SqlAttributeFilter = "off" | "manual" | "all";

/** One row of the properties panel; empty values are left out when shown. */
export type NodeProperties = Record<string, string | number | null | undefined>;

export interface RawNode {
  id: string;
  label: string;
  kind: NodeKind;
  properties: NodeProperties;
  degree: number;
  /** SQL attributes only: the owning term, which is where the attribute is edited. */
  termId?: string;
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
  /** Table-to-table edges only: the key columns and stored queries behind the edge. */
  foreignKeys: S["ForeignKeyRef"][];
  queries: string[];
}

export interface RawGraph {
  nodes: RawNode[];
  edges: RawEdge[];
}

export interface NodeDisplayData extends Attributes {
  x: number;
  y: number;
  label: string;
  kind: NodeKind;
  color: string;
  labelColor?: string;
  size: number;
  borderColor: string;
  highlighted?: boolean;
}

export interface EdgeDisplayData extends Attributes {
  rawId: string;
  kind: EdgeKind;
  originalWeight: number;
  size: number;
  hidden?: boolean;
  color?: string;
}
