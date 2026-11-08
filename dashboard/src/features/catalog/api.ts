// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { getConnection } from "@/features/connections/api";
import { api } from "@/lib/api-client";
import type { S } from "@/types";

export interface SourceCatalog {
  database: S["DatabaseSummary"];
  schemas: S["SchemaSummary"][];
}

/**
 * The source database's catalog entry, or null while it has not been
 * ingested. Matched by name: the store can still hold databases ingested
 * before this build allowed only one.
 */
export async function getSourceDatabase(): Promise<S["DatabaseSummary"] | null> {
  const [connection, databases] = await Promise.all([
    getConnection(),
    api<S["ListResponse_DatabaseSummary_"]>("/datasources/dbs"),
  ]);
  const name = connection.database.toLowerCase();
  return databases.data.find((d) => d.name?.toLowerCase() === name) ?? null;
}

/** The source database's catalog entry and its schemas, or null while it has not been ingested. */
export async function getSourceCatalog(): Promise<SourceCatalog | null> {
  const database = await getSourceDatabase();
  if (!database) return null;
  const payload = await api<S["SchemasPayload"] | null>(`/schemas/${database.id}`);
  return { database, schemas: payload?.schemas ?? [] };
}

export async function listTables(schemaId: string, databaseName: string): Promise<S["TableSummary"][]> {
  const response = await api<S["ListResponse_TableSummary_"]>(
    `/tables/${schemaId}?database_name=${encodeURIComponent(databaseName)}`,
  );
  return response.data;
}

export function getTableColumns(tableId: string, limit?: number): Promise<S["ObjectPageResponse_TableColumns_"]> {
  return api(`/columns/${tableId}${limit ? `?limit=${limit}` : ""}`);
}

/** Patch the description of a table or column node. */
export function updateNode(id: string, body: S["NodeUpdate"]): Promise<S["NodeUpdateResult"] | null> {
  return api(`/nodes/${id}`, { method: "PATCH", json: body });
}
