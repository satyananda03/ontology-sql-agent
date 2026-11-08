// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useState } from "react";
import type { components } from "./schema";

/** Every request and response model, generated from docs/openapi/backend.json. */
export type S = components["schemas"];

type Init = Omit<RequestInit, "body"> & { json?: unknown; body?: BodyInit };

/** Call the backend; throws an Error carrying FastAPI's `detail`. */
export async function api<T>(path: string, { json, ...init }: Init = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: json === undefined ? init.headers : { "content-type": "application/json", ...init.headers },
    body: json === undefined ? init.body : JSON.stringify(json),
  });
  if (!response.ok) throw new Error(await detail(response));
  if (response.status === 204) return undefined as T;
  const type = response.headers.get("content-type") ?? "";
  return (type.includes("json") ? response.json() : response.blob()) as Promise<T>;
}

async function detail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((e: { loc?: string[]; msg: string }) => `${(e.loc ?? []).slice(1).join(".")}: ${e.msg}`)
        .join("\n");
    }
  } catch {
    // Not JSON: fall through to the status line.
  }
  if (response.status >= 502) return "Backend tidak terjangkau. Pastikan server berjalan di :3001.";
  return `${response.status} ${response.statusText}`;
}

/** GET *path* (skipped while null); `reload` refetches, `setData` patches locally. */
export function useFetch<T>(path: string | null) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (path === null) return;
    let live = true;
    setLoading(true);
    setError(undefined);
    api<T>(path)
      .then((d) => live && setData(d))
      .catch((e: Error) => live && setError(e.message))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
  }, [path, tick]);

  return { data, error, loading, setData, reload: () => setTick((t) => t + 1) };
}

/** Save a Blob the browser received as a file download. */
export function download(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), { href: url, download: filename });
  a.click();
  URL.revokeObjectURL(url);
}
