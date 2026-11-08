// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState } from "react";
import { Badge, ErrorBanner } from "@/components/ui";
import { useAction } from "@/hooks/useAction";
import type { S } from "@/types";
import { saveAnalysis, validateAnalysisSql } from "../api";

interface AnalysisFormProps {
  /** The analysis being edited; omitted to create one. */
  analysis?: S["CustomAnalysis"];
  onDone: (saved?: boolean) => void;
}

export function AnalysisForm({ analysis, onDone }: AnalysisFormProps) {
  const [name, setName] = useState(analysis?.name ?? "");
  const [description, setDescription] = useState(analysis?.description ?? "");
  const [sql, setSql] = useState(analysis?.sql ?? "");
  const [valid, setValid] = useState<boolean>();
  const action = useAction();

  async function validate() {
    const result = await action.run(() => validateAnalysisSql(sql));
    if (result) setValid(result.data.valid);
  }

  async function save() {
    const saved = await action.run(() => saveAnalysis(analysis?.id, { name, description, sql }), "Tersimpan");
    if (saved !== undefined) onDone(true);
  }

  return (
    <div className="card stack">
      <h2>{analysis ? "Edit analisis" : "Analisis baru"}</h2>
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
        {valid && <Badge tone="success">Valid</Badge>}
        <button onClick={() => onDone()} disabled={action.busy}>
          Batal
        </button>
      </div>
    </div>
  );
}
