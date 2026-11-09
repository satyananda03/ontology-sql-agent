// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState } from "react";
import { Badge, CertifyChoice, ErrorBanner, useCertifyChoice } from "@/components/ui";
import { useAction } from "@/hooks/useAction";
import type { S } from "@/types";
import { patchSqlAttribute, saveSqlAttribute, validateSqlExpression } from "../api";

interface SqlAttributeFormProps {
  termId: string;
  /** The attribute being edited; omitted to create one. */
  attr?: S["SqlAttribute"];
  /** `certification` is the owning Term's recomputed badge, when the save changed it. */
  onDone: (saved?: S["SqlAttribute"], certification?: string | null) => void;
}

export function SqlAttributeForm({ termId, attr, onDone }: SqlAttributeFormProps) {
  const [name, setName] = useState(attr?.name ?? "");
  const [description, setDescription] = useState(attr?.description ?? "");
  const [expression, setExpression] = useState(attr?.expression ?? "");
  const [valid, setValid] = useState<boolean>();
  const action = useAction();
  const changed =
    !!attr &&
    (name !== attr.name || description !== (attr.description ?? "") || expression !== attr.expression);
  const certify = useCertifyChoice(!!attr?.certified, changed);

  async function validate() {
    const result = await action.run(() => validateSqlExpression(expression, termId, attr?.id ?? null));
    if (result) setValid(result.data.valid);
  }

  async function save() {
    const body = { name, description, expression, term_id: termId };
    const saved = await action.run(() => saveSqlAttribute(attr?.id, body), "Tersimpan");
    if (!saved) return;
    // The full update keeps the stored flag, so a certify change is a second, metadata-only patch.
    if (attr && certify.patch !== undefined) {
      const certified = certify.patch;
      const flagged = await action.run(() => patchSqlAttribute(attr.id, { certified }));
      if (flagged) return onDone(flagged.data, flagged.term_certification);
    }
    onDone(saved.data);
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
      {changed && (
        <CertifyChoice
          checked={certify.checked}
          onChange={certify.setChecked}
          certified={!!attr?.certified}
          disabled={action.busy}
        />
      )}
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
