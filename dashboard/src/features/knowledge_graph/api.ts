// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { api } from "@/lib/api-client";
import type { S } from "@/types";

// Scoped to one database, the backend returns every node instead of capping at 500.
const scoped = (databaseId: string): string => `database_id=${encodeURIComponent(databaseId)}`;

export async function getDataGraph(databaseId: string): Promise<S["DataExplorationGraph"]> {
  const response = await api<S["DataResponse_DataExplorationGraph_"]>(`/exploration/graph?${scoped(databaseId)}`);
  return response.data;
}

export async function getSemanticGraph(databaseId: string): Promise<S["SemanticExplorationGraph"]> {
  const response = await api<S["DataResponse_SemanticExplorationGraph_"]>(
    `/exploration/semantic-graph?${scoped(databaseId)}`,
  );
  return response.data;
}

/** The hop chain behind one term-to-term edge: term, table, column, attribute, term. */
export async function getTermPath(termId: string, otherTermId: string): Promise<S["ExplorationLinkPath"]> {
  const response = await api<S["DataResponse_ExplorationLinkPath_"]>(
    `/exploration/terms/${termId}/path/${otherTermId}`,
  );
  return response.data;
}
