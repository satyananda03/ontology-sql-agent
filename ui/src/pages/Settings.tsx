// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useState } from "react";
import { api, download, useFetch, type S } from "../api";
import { Badge, ErrorBanner, Loading, PageHead, useAction } from "../ui";

export default function Settings() {
  return (
    <>
      <PageHead title="Pengaturan">Perubahan berlaku pada proses berikutnya tanpa restart.</PageHead>
      <Flags />
      <Compilation />
      <ModelTransfer />
    </>
  );
}

const FLAGS: [key: keyof S["Settings"], label: string, hint: string][] = [
  [
    "semantic_compilation_enabled",
    "Kompilasi semantik terjadwal",
    "Ingestion service menyusun ulang ontologi secara berkala. Bila mati, kompilasi hanya berjalan lewat tombol di bawah.",
  ],
  [
    "distinct_value_probing_enabled",
    "Probe nilai unik kolom",
    "Menjalankan SELECT DISTINCT per kolom teks saat kompilasi untuk mengumpulkan contoh nilai. Matikan pada database besar atau berbayar per query.",
  ],
  [
    "pii_detection_enabled",
    "Deteksi PII saat ingest",
    "Menandai kolom yang berisi data pribadi.",
  ],
];

function Flags() {
  const settings = useFetch<S["Settings"]>("/settings");
  const action = useAction();
  const [timeout, setTimeoutValue] = useState("");
  useEffect(() => {
    setTimeoutValue(String(settings.data?.sql_query_timeout_seconds ?? ""));
  }, [settings.data]);

  async function update(body: S["SettingsUpdate"]) {
    const saved = await action.run(() => api<S["Settings"]>("/settings", { method: "PATCH", json: body }), "Tersimpan");
    if (saved) settings.setData(saved);
  }

  return (
    <section className="card stack">
      <h2 style={{ margin: 0 }}>Umum</h2>
      <ErrorBanner message={settings.error ?? action.error} />
      {!settings.data ? (
        <Loading />
      ) : (
        <>
          {FLAGS.map(([key, label, hint]) => (
            <label key={key} className="check" style={{ alignItems: "flex-start" }}>
              <input
                type="checkbox"
                checked={!!settings.data![key]}
                disabled={action.busy}
                onChange={(e) => update({ [key]: e.target.checked })}
                style={{ marginTop: 3 }}
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
            {timeout !== String(settings.data.sql_query_timeout_seconds) && (
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

const when = (iso: string | null) => (iso ? new Date(iso).toLocaleString("id-ID") : "—");

function Compilation() {
  const status = useFetch<S["SemanticStatusResponse"]>("/semantic-compilation/status");
  const action = useAction();

  // Poll while the page is open, so a running pass shows when it finishes.
  // Each poll waits for the previous answer: a slow ingestion service must not
  // pile requests up behind it.
  useEffect(() => {
    if (status.loading) return;
    const timer = window.setTimeout(status.reload, 5000);
    return () => window.clearTimeout(timer);
  }, [status.loading]);

  async function trigger() {
    await action.run(() => api("/semantic-compilation/trigger", { method: "POST" }), "Kompilasi dimulai");
    status.reload();
  }

  async function reset() {
    if (
      !window.confirm(
        "Reset ontologi?\n\nSeluruh lapisan semantik dihapus lalu disusun ulang: term, atribut, hasil review, dan custom analyses. Custom analyses TIDAK dibuat ulang. Deskripsi katalog tetap.\n\nExport model dulu bila perlu cadangan.",
      )
    )
      return;
    await action.run(() => api("/semantic-compilation/reset", { method: "POST" }), "Reset dimulai");
    status.reload();
  }

  const s = status.data;
  return (
    <section className="card stack">
      <div className="row spread">
        <h2 style={{ margin: 0 }}>Kompilasi semantik</h2>
        {s && (s.running ? <Badge tone="solid">Berjalan</Badge> : <Badge>Diam</Badge>)}
      </div>
      <p className="muted" style={{ margin: 0 }}>
        Menyusun term, atribut, dan relasi dari katalog yang sudah di-ingest.
      </p>
      <ErrorBanner message={status.error ?? action.error} />
      {s && (
        <dl className="row" style={{ gap: 24, margin: 0 }}>
          <div>
            <dt className="muted">Terakhir berhasil</dt>
            <dd style={{ margin: 0 }}>{when(s.last_success_at)}</dd>
          </div>
          <div>
            <dt className="muted">Terakhir gagal</dt>
            <dd style={{ margin: 0, color: s.last_failure_at ? "var(--red)" : undefined }}>{when(s.last_failure_at)}</dd>
          </div>
        </dl>
      )}
      <div className="row">
        <button className="primary" onClick={trigger} disabled={action.busy || s?.running}>
          Jalankan kompilasi
        </button>
        <button className="danger" onClick={reset} disabled={action.busy || s?.running}>
          Reset ontologi
        </button>
      </div>
    </section>
  );
}

function ModelTransfer() {
  const action = useAction();
  const [format, setFormat] = useState<S["ModelFormat"]>("auto_ontology");
  const [file, setFile] = useState<File>();
  const [replace, setReplace] = useState(true);
  const [summary, setSummary] = useState<Record<string, unknown>>();

  async function exportModel() {
    const blob = await action.run(() =>
      api<Blob>("/model/export", { method: "POST", json: { format, include_ontology: format === "ossie" } }),
    );
    if (blob) download(blob, format === "ossie" ? "ontology-model.zip" : "ontology-model.yaml");
  }

  async function importModel() {
    if (!file) return;
    if (replace && !window.confirm("Impor dengan mode ganti akan menimpa ontologi yang ada. Lanjutkan?")) return;
    const form = new FormData();
    form.append("file", file);
    const result = await action.run(
      () => api<S["ModelImportResponse"]>(`/model/import?replace=${replace}`, { method: "POST", body: form }),
      "Impor selesai",
    );
    if (result) setSummary(result.summary);
  }

  return (
    <section className="card stack">
      <h2 style={{ margin: 0 }}>Export / import model</h2>
      <p className="muted" style={{ margin: 0 }}>
        Cadangkan ontologi hasil review, atau pindahkan ke lingkungan lain.
      </p>
      <ErrorBanner message={action.error} />
      <div className="row">
        <select value={format} onChange={(e) => setFormat(e.target.value as S["ModelFormat"])} style={{ width: "auto" }} aria-label="Format">
          <option value="auto_ontology">YAML Auto Ontology</option>
          <option value="ossie">Apache Ossie (zip)</option>
        </select>
        <button onClick={exportModel} disabled={action.busy}>
          Export
        </button>
      </div>
      <div className="row">
        <input type="file" accept=".yaml,.yml,.zip" onChange={(e) => setFile(e.target.files?.[0])} style={{ width: "auto" }} aria-label="File model" />
        <label className="check">
          <input type="checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)} />
          Ganti ontologi yang ada
        </label>
        <button onClick={importModel} disabled={action.busy || !file}>
          Import
        </button>
        {action.busy && <span className="spinner" />}
      </div>
      {summary && <pre className="code">{JSON.stringify(summary, null, 2)}</pre>}
    </section>
  );
}
