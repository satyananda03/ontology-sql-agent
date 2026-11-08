// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState } from "react";
import { CertBadge, CertifyCheck, ErrorBanner } from "@/components/ui";
import { useAction } from "@/hooks/useAction";
import type { S } from "@/types";
import { deleteSqlAttribute, patchSqlAttribute } from "../api";
import { SqlAttributeForm } from "./SqlAttributeForm";

interface SqlAttributeCardProps {
  termId: string;
  attr: S["SqlAttribute"];
  onChange: (attr: S["SqlAttribute"], certification?: string | null) => void;
  onDeleted: () => void;
}

export function SqlAttributeCard({ termId, attr, onChange, onDeleted }: SqlAttributeCardProps) {
  const [editing, setEditing] = useState(false);
  const action = useAction();

  async function patch(body: S["SqlAttributeMetadataPatch"]) {
    const saved = await action.run(() => patchSqlAttribute(attr.id, body), "Tersimpan");
    if (saved) onChange(saved.data, saved.term_certification);
  }

  async function remove() {
    if (!window.confirm(`Hapus atribut SQL “${attr.name}”?`)) return;
    const done = await action.run(() => deleteSqlAttribute(attr.id), "Dihapus");
    if (done !== undefined) onDeleted();
  }

  if (editing) {
    return (
      <SqlAttributeForm
        termId={termId}
        attr={attr}
        onDone={(saved) => {
          setEditing(false);
          if (saved) onChange(saved);
        }}
      />
    );
  }

  const suggestion = attr.description_suggestion;
  return (
    <div className="card stack">
      <div className="row spread">
        <div className="row">
          <strong>{attr.name}</strong>
          <CertBadge value={attr.certified} />
        </div>
        <div className="row">
          <CertifyCheck
            label="Certify"
            checked={attr.certified}
            disabled={action.busy}
            onChange={(certified) => patch({ certified })}
          />
          <button onClick={() => setEditing(true)}>Edit</button>
          <button className="danger" onClick={remove} disabled={action.busy}>
            Hapus
          </button>
        </div>
      </div>
      <ErrorBanner message={action.error} />
      <p>{attr.description || <span className="muted">Tanpa deskripsi.</span>}</p>
      {suggestion && suggestion !== attr.description && (
        <div className="card dashed stack">
          <div className="muted small">Saran deskripsi</div>
          <p>{suggestion}</p>
          <div>
            <button disabled={action.busy} onClick={() => patch({ description: suggestion })}>
              Terapkan saran
            </button>
          </div>
        </div>
      )}
      <pre className="code">{attr.expression}</pre>
    </div>
  );
}
