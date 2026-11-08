// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

type Init = Omit<RequestInit, "body"> & { json?: unknown; body?: BodyInit };

/** Call the backend under `/api`; throws an Error carrying FastAPI's `detail`. */
export async function api<T>(path: string, { json, ...init }: Init = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: json === undefined ? init.headers : { "content-type": "application/json", ...init.headers },
    body: json === undefined ? init.body : JSON.stringify(json),
  });
  if (!response.ok) throw new Error(await detail(response));
  // null, not undefined: useAction reports a failed action as undefined.
  if (response.status === 204) return null as T;
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
