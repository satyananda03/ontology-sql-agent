// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { api } from "@/lib/api-client";
import type { S } from "@/types";

type AcronymBody = { name: string; description: string };

export function listAcronyms(): Promise<S["Acronym"][]> {
  return api("/acronyms");
}

export function createAcronym(body: AcronymBody): Promise<S["Acronym"]> {
  return api("/acronyms", { method: "POST", json: body });
}

export function updateAcronym(id: string, body: AcronymBody): Promise<S["Acronym"]> {
  return api(`/acronyms/${id}`, { method: "PATCH", json: body });
}

export function deleteAcronym(id: string): Promise<null> {
  return api(`/acronyms/${id}`, { method: "DELETE" });
}
