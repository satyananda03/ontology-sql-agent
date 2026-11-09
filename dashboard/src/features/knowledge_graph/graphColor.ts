// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import type { EdgeKind, NodeKind } from "./types";

/** Node colour per kind. Reds stay out: the selection border is red. */
export const NODE_COLORS: Record<NodeKind, string> = {
  term: "#00E0A4",
  table: "#7C8CFF",
};

/** Edge colour per kind; the legend shows the same. Muted, except the two that call for attention. */
export const EDGE_COLORS: Record<EdgeKind, string> = {
  termTable: "#4C5AA8",
  sharedTable: "#1F7A5F",
  semanticFk: "#00E676",
  foreignKey: "#6B6B6B",
  sqlOnly: "#FFD600",
};
