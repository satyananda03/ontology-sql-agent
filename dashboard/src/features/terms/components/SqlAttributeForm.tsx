// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState } from "react";
import { Badge, ErrorBanner } from "@/components/ui";
import { useAction } from "@/hooks/useAction";
import type { S } from "@/types";
import { saveSqlAttribute, validateSqlExpression } from "../api";

interface SqlAttributeFormProps {
  termId: string;
  /** The attribute being edited; omitted to create one. */
  attr?: S["SqlAttribute"];
  onDone: (saved?: S["SqlAttribute"]) => void;
}

export function SqlAttributeForm({ termId, attr, onDone }: SqlAttributeFormProps) {
  const [name, setName] = useState(attr?.name ?? "");
  const [description, setDescription] = useState(attr?.description ?? "");
  const [expression, setExpression] = useState(attr?.expression ?? "");
  const [valid, setValid] = useState<boolean>();
  const action = useAction();

  async function validate() {
    const result = await action.run(() => validateSqlExpression(expression, termId, attr?.id ?? null));
    if (result) setValid(result.data.valid);
  }

  async function save() {
    const body = { name, description, expression, term_id: termId };
    const saved = await action.run(() => saveSqlAttribute(attr?.id, body), "Tersimpan");
    if (saved) onDone(saved.data);
  }

  return (
    <div className="card stack">
      <label className="field">
        Nama
        <input value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <label className="field">
        Deskripsi
        <textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
      </label>
      <label className="field">
        Ekspresi SQL
        <span className="hint">Ekspresi agregat atas kolom tabel term ini, misalnya SUM(amount).</span>
        <textarea
          className="mono"
          rows={4}
          value={expression}
          onChange={(e) => {
            setExpression(e.target.value);
            setValid(undefined);
          }}
        />
      </label>
      <ErrorBanner message={action.error} />
      {valid === false && <div className="banner">Ekspresi tidak valid untuk tabel term ini.</div>}
      <div className="row">
        <button className="primary" onClick={save} disabled={action.busy || !name.trim() || !expression.trim()}>
          Simpan
        </button>
        <button onClick={validate} disabled={action.busy || !expression.trim()}>
          Validasi
        </button>
        {valid && <Badge tone="success">Valid</Badge>}
        <button onClick={() => onDone()} disabled={action.busy}>
          Batal
        </button>
      </div>
    </div>
  );
}
