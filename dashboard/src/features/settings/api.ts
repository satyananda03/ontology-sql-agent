// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { api } from "@/lib/api-client";
import type { S } from "@/types";

export function getSettings(): Promise<S["Settings"]> {
  return api("/settings");
}

export function updateSettings(body: S["SettingsUpdate"]): Promise<S["Settings"]> {
  return api("/settings", { method: "PATCH", json: body });
}

export function getIngestStatus(): Promise<S["IngestStatus"]> {
  return api("/ingest/status");
}

export function triggerIngest(): Promise<S["IngestStatus"]> {
  return api("/ingest", { method: "POST" });
}

export function getCompilationStatus(): Promise<S["SemanticStatusResponse"]> {
  return api("/semantic-compilation/status");
}

export function triggerCompilation(): Promise<unknown> {
  return api("/semantic-compilation/trigger", { method: "POST" });
}

/** Delete the whole ontology, then compile it again from scratch. */
export function regenerateOntology(): Promise<unknown> {
  return api("/semantic-compilation/reset", { method: "POST" });
}

export function exportModel(): Promise<Blob> {
  return api("/model/export", { method: "POST", json: {} });
}

export function importModel(file: File, replace: boolean): Promise<S["ModelImportResponse"]> {
  const form = new FormData();
  form.append("file", file);
  return api(`/model/import?replace=${replace}`, { method: "POST", body: form });
}
