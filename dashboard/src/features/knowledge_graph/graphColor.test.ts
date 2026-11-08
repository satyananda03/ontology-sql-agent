// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

// Ported from frontend_references/src/features/knowledge_graph/graphColor.test.ts.

import { describe, expect, test } from "vitest";
import { resolveNodeColor } from "./graphColor";

describe("resolveNodeColor", () => {
  test("gives each schema its own colour, keyed in lower case", () => {
    let map = new Map<string, string>();
    const colors = ["public", "analytics", "Staging"].map((schema) => {
      const result = resolveNodeColor(schema, map);
      map = result.map;
      return result.color;
    });

    expect(new Set(colors).size).toBe(3);
    expect([...map.keys()]).toEqual(["public", "analytics", "staging"]);
  });

  test("keeps the fixed term colour apart from the schema colours", () => {
    const term = resolveNodeColor("term", new Map());
    const schema = resolveNodeColor("public", term.map);

    expect(schema.color).not.toBe(term.color);
  });

  test("returns the cached colour in any case without changing the map", () => {
    const first = resolveNodeColor("Public", new Map());
    const again = resolveNodeColor("PUBLIC", first.map);

    expect(again).toEqual({ color: first.color, map: first.map, updated: false });
  });

  test("treats a missing group as unknown", () => {
    const missing = resolveNodeColor(undefined, new Map());
    const unknown = resolveNodeColor("UNKNOWN", missing.map);

    expect(unknown.color).toBe(missing.color);
  });
});
