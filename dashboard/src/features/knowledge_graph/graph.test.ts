// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { describe, expect, test } from "vitest";
import type { S } from "@/types";
import { combinedGraphToRaw, hashPosition, sigmaGraphFromRaw } from "./graph";

const table = (id: string, schema: string): S["DataGraphNode"] => ({ id, name: id, schema_name: schema, zones: [] });
const term = (id: string): S["SemanticGraphNode"] => ({ id, name: id, zones: [] });

const dataGraph: S["DataExplorationGraph"] = {
  nodes: [table("orders", "public"), table("customers", "public"), table("events", "analytics")],
  links: [
    { source: "orders", target: "customers", via_foreign_key: true, foreign_keys: [{}], queries: [], relationship_types: ["FOREIGN_KEY"] },
    { source: "orders", target: "events", via_foreign_key: false, foreign_keys: [], queries: ["SELECT 1"], relationship_types: ["SQL"] },
    { source: "orders", target: "missing", via_foreign_key: true, foreign_keys: [{}], queries: [], relationship_types: ["FOREIGN_KEY"] },
    { source: "orders", target: "customers", via_foreign_key: true, foreign_keys: [{}], queries: [], relationship_types: ["FOREIGN_KEY"] },
  ],
};

const semanticGraph: S["SemanticExplorationGraph"] = {
  nodes: [term("Order"), term("Customer"), term("Product")],
  links: [
    { source: "Order", target: "Customer", relationship_types: ["REPRESENTS", "SEMANTIC_FK"] },
    { source: "Customer", target: "Product", relationship_types: ["REPRESENTS"] },
  ],
  term_tables: [
    { term_id: "Order", table_id: "orders", paths: ["REPRESENTS"] },
    { term_id: "Customer", table_id: "orders", paths: ["SEMANTIC_FK"] },
    { term_id: "Customer", table_id: "customers", paths: ["HAS_ATTRIBUTE", "SEMANTIC_FK"] },
    { term_id: "Product", table_id: "missing", paths: ["REPRESENTS"] },
  ],
};

const combined = () => combinedGraphToRaw(semanticGraph, dataGraph);
const kindOf = (raw: ReturnType<typeof combined>, source: string, target: string) =>
  raw.edges.find((edge) => edge.source === source && edge.target === target)?.kind;

describe("combinedGraphToRaw", () => {
  test("puts terms and tables in one graph, each with its kind", () => {
    const kinds = Object.fromEntries(combined().nodes.map((node) => [node.id, node.kind]));
    expect(kinds).toEqual({
      Order: "term",
      Customer: "term",
      Product: "term",
      orders: "table",
      customers: "table",
      events: "table",
    });
  });

  test("links a term to the tables it is built from, inferred only when that is the sole way in", () => {
    const raw = combined();
    expect(kindOf(raw, "Order", "orders")).toBe("termTable");
    expect(kindOf(raw, "Customer", "orders")).toBe("semanticFk");
    expect(kindOf(raw, "Customer", "customers")).toBe("termTable");
    expect(kindOf(raw, "Product", "missing")).toBeUndefined();
  });

  test("keeps term-to-term links, marking the ones through an inferred join", () => {
    const raw = combined();
    expect(kindOf(raw, "Order", "Customer")).toBe("semanticFk");
    expect(kindOf(raw, "Customer", "Product")).toBe("sharedTable");
  });

  test("shows every table relation: foreign keys and shared SQL queries", () => {
    expect(kindOf(combined(), "orders", "customers")).toBe("foreignKey");
    expect(kindOf(combined(), "orders", "events")).toBe("sqlOnly");
  });

  test("drops edges to a missing node and duplicate edges, and counts degrees from the rest", () => {
    const raw = combined();
    expect(raw.edges.filter((edge) => edge.kind === "foreignKey")).toHaveLength(1);
    expect(Object.fromEntries(raw.nodes.map((node) => [node.id, node.degree]))).toMatchObject({
      orders: 4,
      customers: 2,
      events: 1,
    });
  });
});

describe("SQL attributes", () => {
  const attribute = (id: string, termId: string | null, sql: string): S["SqlAttribute"] => ({
    id,
    name: id,
    term_id: termId,
    sql,
    source: "manual",
  });
  const raw = () =>
    combinedGraphToRaw(semanticGraph, dataGraph, [
      attribute("ActiveOrders", "Order", "SELECT 1"),
      attribute("OrderCount", "Order", "SELECT COUNT(*) FROM orders"),
      attribute("Elsewhere", "OtherDbTerm", "SELECT 1"),
    ]);

  test("becomes a node hanging off its term, carrying the term for the edit link", () => {
    const node = raw().nodes.find((n) => n.id === "ActiveOrders");
    expect(node).toMatchObject({ kind: "sqlAttribute", termId: "Order" });
    expect(kindOf(raw(), "Order", "ActiveOrders")).toBe("termSqlAttribute");
  });

  test("links to the tables its SQL reaches, except the term's own", () => {
    // "SELECT 1" joins orders and events; Order already owns orders.
    expect(kindOf(raw(), "ActiveOrders", "events")).toBe("sqlAttributeTable");
    expect(kindOf(raw(), "ActiveOrders", "orders")).toBeUndefined();
    expect(raw().edges.filter((edge) => edge.source === "OrderCount")).toHaveLength(0);
  });

  test("leaves out attributes whose term is not in this graph", () => {
    expect(raw().nodes.some((n) => n.id === "Elsewhere")).toBe(false);
  });
});

describe("sigmaGraphFromRaw", () => {
  test("builds every node and edge, sizing the busiest node largest", () => {
    const graph = sigmaGraphFromRaw(combined());

    expect(graph.order).toBe(6);
    expect(graph.getNodeAttribute("orders", "size")).toBeGreaterThan(graph.getNodeAttribute("events", "size"));
    expect(graph.getNodeAttribute("orders", "kind")).toBe("table");
  });

  test("starts each node at the same position every time", () => {
    expect(hashPosition("orders")).toEqual(hashPosition("orders"));
    expect(hashPosition("orders")).not.toEqual(hashPosition("customers"));
  });
});
