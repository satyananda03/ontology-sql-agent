// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { api } from "@/lib/api-client";
import type { S } from "@/types";

export const MIN_SEARCH_LENGTH = 2;

export async function globalSearch(term: string, inDescriptions: boolean): Promise<S["GlobalSearchItem"][]> {
  const response = await api<S["ListResponse_GlobalSearchItem_"]>("/search/global-search", {
    method: "POST",
    json: { search_term: term, filters: { description: inDescriptions, synonyms: true } },
  });
  return response.data;
}
