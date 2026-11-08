// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, useFetch, type S } from "../api";
import { Empty, ErrorBanner, Loading, PageHead, useAction } from "../ui";

type Analysis = S["CustomAnalysis"];

export default function Analyses() {
  const [params, setParams] = useSearchParams();
  const query = params.get("q") ?? "";
  const focus = params.get("id");
  const [draft, setDraft] = useState(query);
  const [adding, setAdding] = useState(false);
  const list = useFetch<S["PagedListResponse_CustomAnalysis_"]>(
    `/custom-analyses${query ? `?query=${encodeURIComponent(query)}` : ""}`,
  );

  return (
    <>
      <PageHead title="Custom analyses">
        Contoh pertanyaan beserta SQL yang sudah diverifikasi. Agent mengambil yang relevan sebagai referensi saat
        menyusun query, jadi contoh yang baik langsung menaikkan akurasi.
      </PageHead>
      <div className="row spread" style={{ marginBottom: 16 }}>
        <form
          className="row"
          onSubmit={(e) => {
            e.preventDefault();
            setParams(draft ? { q: draft } : {});
          }}
        >
          <input
            type="search"
            placeholder="Cari analisis…"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            style={{ maxWidth: 320 }}
            aria-label="Cari analisis"
          />
          <button type="submit">Cari</button>
        </form>
        {!adding && (
          <button className="primary" onClick={() => setAdding(true)}>
            + Tambah analisis
          </button>
        )}
      </div>
      {adding && (
        <AnalysisForm
          onDone={(saved) => {
            setAdding(false);
            if (saved) list.reload();
          }}
        />
      )}
      <ErrorBanner message={list.error} />
      {list.loading && !list.data && <Loading />}
      {list.data?.data.length === 0 && !adding && <Empty>Belum ada custom analysis.</Empty>}
      {list.data?.data.map((analysis) => (
        <AnalysisCard key={analysis.id} analysis={analysis} highlighted={analysis.id === focus} onChange={list.reload} />
      ))}
    </>
  );
}

function AnalysisCard({
  analysis,
  highlighted,
  onChange,
}: {
  analysis: Analysis;
  highlighted: boolean;
  onChange: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const action = useAction();

  async function remove() {
    if (!window.confirm(`Hapus analisis “${analysis.name}”?`)) return;
    const done = await action.run(() => api(`/custom-analyses/${analysis.id}`, { method: "DELETE" }), "Dihapus");
    if (done !== undefined) onChange();
  }

  if (editing) {
    return (
      <AnalysisForm
        analysis={analysis}
        onDone={(saved) => {
          setEditing(false);
          if (saved) onChange();
        }}
      />
    );
  }
  return (
    <div className="card" style={highlighted ? { borderColor: "var(--black)" } : undefined}>
      <div className="row spread">
        <strong>{analysis.name}</strong>
        <div className="row">
          <button onClick={() => setEditing(true)}>Edit</button>
          <button className="danger" onClick={remove} disabled={action.busy}>
            Hapus
          </button>
        </div>
      </div>
      <ErrorBanner message={action.error} />
      {analysis.description && <p style={{ marginTop: 8 }}>{analysis.description}</p>}
      <pre className="code">{analysis.sql}</pre>
    </div>
  );
}

function AnalysisForm({ analysis, onDone }: { analysis?: Analysis; onDone: (saved?: boolean) => void }) {
  const [name, setName] = useState(analysis?.name ?? "");
  const [description, setDescription] = useState(analysis?.description ?? "");
  const [sql, setSql] = useState(analysis?.sql ?? "");
  const [valid, setValid] = useState<boolean>();
  const action = useAction();

  async function validate() {
    const result = await action.run(() =>
      api<S["DataResponse_SqlValidationResult_"]>("/custom-analyses/validate", { method: "POST", json: { sql } }),
    );
    if (result) setValid(result.data.valid);
  }

  async function save() {
    const body = { name, description, sql };
    const saved = await action.run(
      () =>
        analysis
          ? api(`/custom-analyses/${analysis.id}`, { method: "PUT", json: body })
          : api("/custom-analyses", { method: "POST", json: body }),
      "Tersimpan",
    );
    if (saved !== undefined) onDone(true);
  }

  return (
    <div className="card stack">
      <h2 style={{ margin: 0 }}>{analysis ? "Edit analisis" : "Analisis baru"}</h2>
      <label className="field">
        Pertanyaan / nama
        <span className="hint">Tulis seperti pertanyaan pengguna, misalnya “Jumlah transaksi per provinsi bulan ini”.</span>
        <input value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <label className="field">
        Deskripsi
        <textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
      </label>
      <label className="field">
        SQL
        <textarea
          className="mono"
          rows={8}
          value={sql}
          onChange={(e) => {
            setSql(e.target.value);
            setValid(undefined);
          }}
        />
      </label>
      <ErrorBanner message={action.error} />
      {valid === false && <div className="banner">SQL tidak valid terhadap katalog.</div>}
      <div className="row">
        <button className="primary" onClick={save} disabled={action.busy || !name.trim() || !sql.trim()}>
          Simpan
        </button>
        <button onClick={validate} disabled={action.busy || !sql.trim()}>
          Validasi SQL
        </button>
        {valid && <span className="badge solid">Valid</span>}
        <button onClick={() => onDone()} disabled={action.busy}>
          Batal
        </button>
      </div>
    </div>
  );
}
