// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { describe, expect, test } from "vitest";
import type { S } from "@/types";
import { dataGraphToRaw, hashPosition, semanticGraphToRaw, sigmaGraphFromRaw } from "./graph";

const table = (id: string, schema: string): S["DataGraphNode"] => ({ id, name: id, schema_name: schema, zones: [] });

const dataGraph: S["DataExplorationGraph"] = {
  nodes: [table("orders", "public"), table("customers", "public"), table("events", "analytics")],
  links: [
    { source: "orders", target: "customers", via_foreign_key: true, foreign_keys: [{}], queries: [], relationship_types: ["FOREIGN_KEY"] },
    { source: "orders", target: "events", via_foreign_key: false, foreign_keys: [], queries: ["SELECT 1"], relationship_types: ["SQL"] },
    { source: "orders", target: "missing", via_foreign_key: true, foreign_keys: [{}], queries: [], relationship_types: ["FOREIGN_KEY"] },
    { source: "orders", target: "customers", via_foreign_key: true, foreign_keys: [{}], queries: [], relationship_types: ["FOREIGN_KEY"] },
  ],
};

describe("dataGraphToRaw", () => {
  test("shows foreign-key edges only, unless shared-SQL edges are asked for", () => {
    expect(dataGraphToRaw(dataGraph, { includeSqlEdges: false }).edges.map((edge) => edge.kind)).toEqual(["foreignKey"]);
    expect(dataGraphToRaw(dataGraph, { includeSqlEdges: true }).edges.map((edge) => edge.kind)).toEqual([
      "foreignKey",
      "sqlOnly",
    ]);
  });

  test("drops edges to a missing node and duplicate edges, and counts degrees from the rest", () => {
    const raw = dataGraphToRaw(dataGraph, { includeSqlEdges: false });

    expect(raw.edges).toHaveLength(1);
    expect(Object.fromEntries(raw.nodes.map((node) => [node.id, node.degree]))).toEqual({
      orders: 1,
      customers: 1,
      events: 0,
    });
  });

  test("colours nodes by schema, in first-seen order", () => {
    expect([...dataGraphToRaw(dataGraph, { includeSqlEdges: false }).groupColors.keys()]).toEqual([
      "public",
      "analytics",
    ]);
  });
});

describe("semanticGraphToRaw", () => {
  test("marks a term link carrying a semantic foreign key as an inferred join", () => {
    const raw = semanticGraphToRaw({
      nodes: [
        { id: "a", name: "Customer", zones: [] },
        { id: "b", name: "Order", zones: [] },
        { id: "c", name: "Product", zones: [] },
      ],
      links: [
        { source: "a", target: "b", relationship_types: ["REPRESENTS", "SEMANTIC_FK"] },
        { source: "b", target: "c", relationship_types: ["REPRESENTS"] },
      ],
    });

    expect(raw.edges.map((edge) => edge.kind)).toEqual(["semanticFk", "sharedTable"]);
    expect([...raw.groupColors.keys()]).toEqual(["term"]);
  });
});

describe("sigmaGraphFromRaw", () => {
  test("builds every node and edge, sizing the busiest node largest", () => {
    const graph = sigmaGraphFromRaw(dataGraphToRaw(dataGraph, { includeSqlEdges: true }));

    expect(graph.order).toBe(3);
    expect(graph.size).toBe(2);
    expect(graph.getNodeAttribute("orders", "size")).toBeGreaterThan(graph.getNodeAttribute("events", "size"));
  });

  test("starts each node at the same position every time", () => {
    expect(hashPosition("orders")).toEqual(hashPosition("orders"));
    expect(hashPosition("orders")).not.toEqual(hashPosition("customers"));
  });
});
