// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { S } from "@/types";

type GlossaryEntryBody = { name: string; description: string };

export function listGlossary(): Promise<S["GlossaryEntry"][]> {
  return api("/glossary");
}

export function createGlossaryEntry(body: GlossaryEntryBody): Promise<S["GlossaryEntry"]> {
  return api("/glossary", { method: "POST", json: body });
}

export function updateGlossaryEntry(id: string, body: GlossaryEntryBody): Promise<S["GlossaryEntry"]> {
  return api(`/glossary/${id}`, { method: "PATCH", json: body });
}

export function deleteGlossaryEntry(id: string): Promise<null> {
  return api(`/glossary/${id}`, { method: "DELETE" });
}

export const glossaryQueries = {
  entries: () => queryOptions({ queryKey: ["glossary", "entries"], queryFn: listGlossary }),
};
