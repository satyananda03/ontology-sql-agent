// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState } from "react";
import { ErrorBanner, Spinner } from "@/components/ui";
import { useAction } from "@/hooks/useAction";
import { download } from "@/lib/utils";
import { exportModel, importModel } from "../api";

export function ModelTransferPanel() {
  const action = useAction();
  const [file, setFile] = useState<File>();
  const [replace, setReplace] = useState(true);
  const [summary, setSummary] = useState<Record<string, unknown>>();

  async function runExport() {
    const blob = await action.run(exportModel);
    if (blob) download(blob, "ontology-model.yaml");
  }

  async function runImport() {
    if (!file) return;
    if (replace && !window.confirm("Impor dengan mode ganti akan menimpa ontologi yang ada. Lanjutkan?")) return;
    const result = await action.run(() => importModel(file, replace), "Impor selesai");
    if (result) setSummary(result.summary);
  }

  return (
    <section className="card stack">
      <h2>Export / import model</h2>
      <p className="muted">Cadangkan ontologi hasil review, atau pindahkan ke lingkungan lain.</p>
      <ErrorBanner message={action.error} />
      <div>
        <button onClick={runExport} disabled={action.busy}>
          Export YAML
        </button>
      </div>
      <div className="row">
        <input
          type="file"
          accept=".yaml,.yml"
          onChange={(e) => setFile(e.target.files?.[0])}
          style={{ width: "auto" }}
          aria-label="File model"
        />
        <label className="check">
          <input type="checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)} />
          Ganti ontologi yang ada
        </label>
        <button onClick={runImport} disabled={action.busy || !file}>
          Import
        </button>
        {action.busy && <Spinner />}
      </div>
      {summary && <pre className="code">{JSON.stringify(summary, null, 2)}</pre>}
    </section>
  );
}
