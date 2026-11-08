// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import type { EdgeKind } from "./types";

const DEFAULT_NODE_COLOR = "#5D6D7E";

/** Groups with a fixed colour. Every other group (a schema) takes the next free palette colour. */
const NODE_GROUP_COLORS: Record<string, string> = {
  term: "#00e0a4",
};

// frontend_references' entity-type colours first, as the most distinct, then its
// extended set. Reds come last: the selection border is red.
const PALETTE = [
  "#82ea1a",
  "#ff7513",
  "#635dff",
  "#ffd12b",
  "#e875ff",
  "#00959d",
  "#C98B5E",
  "#002fff",
  "#bcd98a",
  "#9575CD",
  "#16A085",
  "#D35400",
  "#7F8C8D",
  "#1ABC9C",
  "#9B59B6",
  "#E67E22",
  "#FF2B67",
  "#FF8FAB",
  "#FB2020",
  "#FF5858",
  "#C0392B",
];

const PREDEFINED_COLOR_SET = new Set(Object.values(NODE_GROUP_COLORS));

/** Edge colour per kind, from the frontend_references dark palette; the legend shows the same. */
export const EDGE_COLORS: Record<EdgeKind, string> = {
  foreignKey: "#555555",
  sqlOnly: "#FFD600",
  sharedTable: "#555555",
  semanticFk: "#00E676",
};

interface ResolveNodeColorResult {
  color: string;
  map: Map<string, string>;
  updated: boolean;
}

/**
 * The colour of *group*, assigning one on first sight. Returns a new map when
 * it assigned, so a caller holding the old one never sees it change.
 */
export function resolveNodeColor(group: string | undefined, currentMap: Map<string, string>): ResolveNodeColorResult {
  const normalizedGroup = group ? group.toLowerCase() : "unknown";
  const known = currentMap.get(normalizedGroup);
  if (known) return { color: known, map: currentMap, updated: false };

  const usedColors = new Set([...currentMap.values()].filter((color) => !PREDEFINED_COLOR_SET.has(color)));
  const color =
    NODE_GROUP_COLORS[normalizedGroup] ?? PALETTE.find((candidate) => !usedColors.has(candidate)) ?? DEFAULT_NODE_COLOR;

  const map = new Map(currentMap);
  map.set(normalizedGroup, color);
  return { color, map, updated: true };
}
