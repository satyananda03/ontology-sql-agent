// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useState } from "react";
import { ErrorBanner, Loading } from "@/components/ui";
import { useAction } from "@/hooks/useAction";
import { useFetch } from "@/hooks/useFetch";
import type { S } from "@/types";
import { getSettings, updateSettings } from "../api";

const FLAGS: [key: keyof S["Settings"], label: string, hint: string][] = [
  [
    "distinct_value_probing_enabled",
    "Probe nilai unik kolom",
    "Menjalankan SELECT DISTINCT per kolom teks saat kompilasi untuk mengumpulkan contoh nilai. Matikan pada database besar atau berbayar per query.",
  ],
  ["pii_detection_enabled", "Deteksi PII saat ingest", "Menandai kolom yang berisi data pribadi."],
];

export function GeneralSettings() {
  const settings = useFetch(getSettings);
  const action = useAction();
  const [timeout, setTimeoutValue] = useState("");
  const savedTimeout = String(settings.data?.sql_query_timeout_seconds ?? "");
  useEffect(() => setTimeoutValue(savedTimeout), [savedTimeout]);

  async function update(body: S["SettingsUpdate"]) {
    const saved = await action.run(() => updateSettings(body), "Tersimpan");
    if (saved) settings.setData(saved);
  }

  const data = settings.data;
  return (
    <section className="card stack">
      <h2>Umum</h2>
      <ErrorBanner message={settings.error ?? action.error} />
      {!data ? (
        <Loading />
      ) : (
        <>
          {FLAGS.map(([key, label, hint]) => (
            <label key={key} className="check top">
              <input
                type="checkbox"
                checked={!!data[key]}
                disabled={action.busy}
                onChange={(e) => update({ [key]: e.target.checked })}
              />
              <span>
                <strong>{label}</strong>
                <br />
                <span className="muted">{hint}</span>
              </span>
            </label>
          ))}
          <form
            className="row"
            onSubmit={(e) => {
              e.preventDefault();
              update({ sql_query_timeout_seconds: Number(timeout) });
            }}
          >
            <label className="field" style={{ flex: "0 1 260px" }}>
              Batas waktu query SQL agent (detik)
              <span className="hint">1–3600. Query yang melewati batas dihentikan database.</span>
              <input type="number" min={1} max={3600} value={timeout} onChange={(e) => setTimeoutValue(e.target.value)} />
            </label>
            {timeout !== savedTimeout && (
              <button className="primary" disabled={action.busy} style={{ alignSelf: "flex-end" }}>
                Simpan
              </button>
            )}
          </form>
        </>
      )}
    </section>
  );
}
