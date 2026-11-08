// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useState } from "react";
import { useFetch } from "@/hooks/useFetch";
import { replaceById } from "@/lib/utils";
import type { S } from "@/types";
import { getSourceCatalog, getTableColumns, listTables } from "../api";

type Table = S["TableSummary"];

/**
 * The source database's schema → table tree, tables loaded when a schema
 * opens. When *tableId* names a table not loaded yet (a link from a term or a
 * search hit), the tree opens its schema.
 */
export function useCatalogTree(tableId: string | null) {
  const source = useFetch(getSourceCatalog);
  const [tables, setTables] = useState<Record<string, Table[]>>({});
  const [open, setOpen] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string>();
  const databaseName = source.data?.database.name ?? "";

  async function loadTables(schemaId: string): Promise<void> {
    if (tables[schemaId]) return;
    const list = await listTables(schemaId, databaseName);
    setTables((prev) => ({ ...prev, [schemaId]: list }));
  }

  function toggleSchema(schemaId: string) {
    const willOpen = !open.has(schemaId);
    setOpen((prev) => {
      const next = new Set(prev);
      if (willOpen) next.add(schemaId);
      else next.delete(schemaId);
      return next;
    });
    if (willOpen) loadTables(schemaId).catch((e: Error) => setError(e.message));
  }

  useEffect(() => {
    const schemas = source.data?.schemas;
    if (!tableId || !schemas) return;
    if (Object.values(tables).some((list) => list.some((t) => t.id === tableId))) return;
    (async () => {
      const page = await getTableColumns(tableId, 1);
      const schema = schemas.find((s) => s.schema_name === page.data.schema_name);
      if (!schema) return;
      await loadTables(schema.id);
      setOpen((prev) => new Set([...prev, schema.id]));
    })().catch((e: Error) => setError(e.message));
    // Deliberately narrow deps: reveal only when the target changes.
  }, [tableId, source.data]);

  const selected = Object.values(tables)
    .flat()
    .find((t) => t.id === tableId);

  function updateTable(table: Table) {
    setTables((prev) => Object.fromEntries(Object.entries(prev).map(([key, list]) => [key, replaceById(list, table)])));
  }

  return {
    source,
    tables,
    isOpen: (id: string) => open.has(id),
    toggleSchema,
    selected,
    updateTable,
    error: source.error ?? error,
  };
}

export type CatalogTree = ReturnType<typeof useCatalogTree>;
