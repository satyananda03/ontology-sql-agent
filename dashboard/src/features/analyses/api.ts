// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { api } from "@/lib/api-client";
import type { S } from "@/types";

type AnalysisBody = { name: string; description: string; sql: string };

export function listAnalyses(query: string): Promise<S["PagedListResponse_CustomAnalysis_"]> {
  return api(`/custom-analyses${query ? `?query=${encodeURIComponent(query)}` : ""}`);
}

/** Create an analysis, or replace *id* when given. */
export function saveAnalysis(id: string | undefined, body: AnalysisBody): Promise<unknown> {
  return id
    ? api(`/custom-analyses/${id}`, { method: "PUT", json: body })
    : api("/custom-analyses", { method: "POST", json: body });
}

export function deleteAnalysis(id: string): Promise<unknown> {
  return api(`/custom-analyses/${id}`, { method: "DELETE" });
}

export function validateAnalysisSql(sql: string): Promise<S["DataResponse_SqlValidationResult_"]> {
  return api("/custom-analyses/validate", { method: "POST", json: { sql } });
}
