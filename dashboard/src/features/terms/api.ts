// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { api } from "@/lib/api-client";
import type { S } from "@/types";

export const TERMS_PAGE_SIZE = 50;

export function listTerms(query: string, skip: number): Promise<S["TermsPageResponse"]> {
  const params = new URLSearchParams({ skip: String(skip), limit: String(TERMS_PAGE_SIZE) });
  if (query) params.set("query", query);
  return api(`/terms?${params}`);
}

export function getTerm(id: string): Promise<S["DataResponse_TermDetail_"]> {
  return api(`/terms/${id}`);
}

export function updateTerm(id: string, body: S["TermUpdate"]): Promise<S["DataResponse_Term_"]> {
  return api(`/terms/${id}`, { method: "PATCH", json: body });
}

export function listColumnAttributes(termId: string): Promise<S["PagedListResponse_ColumnAttribute_"]> {
  return api(`/terms/${termId}/column-attributes`);
}

export function updateColumnAttribute(
  termId: string,
  attributeId: string,
  body: S["ColumnAttributeUpdate"],
): Promise<S["ColumnAttributePatchResponse"]> {
  return api(`/terms/${termId}/column-attributes/${attributeId}`, { method: "PATCH", json: body });
}

export function listSqlAttributes(termId: string): Promise<S["PagedListResponse_SqlAttribute_"]> {
  return api(`/terms/${termId}/sql-attributes`);
}

export function patchSqlAttribute(
  id: string,
  body: S["SqlAttributeMetadataPatch"],
): Promise<S["SqlAttributePatchResponse"]> {
  return api(`/sql-attributes/${id}`, { method: "PATCH", json: body });
}

/** Create a SQL attribute, or replace *id* when given. */
export function saveSqlAttribute(
  id: string | undefined,
  body: { name: string; description: string; expression: string; term_id: string },
): Promise<S["DataResponse_SqlAttribute_"]> {
  return id
    ? api(`/sql-attributes/${id}`, { method: "PUT", json: body })
    : api("/sql-attributes", { method: "POST", json: body });
}

export function deleteSqlAttribute(id: string): Promise<unknown> {
  return api(`/sql-attributes/${id}`, { method: "DELETE" });
}

export function validateSqlExpression(
  expression: string,
  termId: string,
  attributeId: string | null,
): Promise<S["DataResponse_SqlExpressionValidationResult_"]> {
  return api("/sql-attributes/validate", {
    method: "POST",
    json: { expression, term_id: termId, attribute_id: attributeId },
  });
}
