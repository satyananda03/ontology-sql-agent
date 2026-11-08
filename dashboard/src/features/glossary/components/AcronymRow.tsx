// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState } from "react";
import { ErrorBanner } from "@/components/ui";
import { useAction } from "@/hooks/useAction";
import type { S } from "@/types";
import { deleteAcronym, updateAcronym } from "../api";

/** One glossary entry, editable in place. */
export function AcronymRow({ acronym, onChange }: { acronym: S["Acronym"]; onChange: () => void }) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(acronym.name);
  const [description, setDescription] = useState(acronym.description);
  const action = useAction();

  async function save() {
    const saved = await action.run(() => updateAcronym(acronym.id, { name, description }), "Tersimpan");
    if (!saved) return;
    setEditing(false);
    onChange();
  }

  async function remove() {
    if (!window.confirm(`Hapus “${acronym.name}” dari glossary?`)) return;
    const done = await action.run(() => deleteAcronym(acronym.id), "Dihapus");
    if (done !== undefined) onChange();
  }

  if (editing) {
    return (
      <tr>
        <td>
          <input value={name} onChange={(e) => setName(e.target.value)} aria-label="Istilah" />
        </td>
        <td>
          <input value={description} onChange={(e) => setDescription(e.target.value)} aria-label="Arti" />
          <ErrorBanner message={action.error} />
        </td>
        <td>
          <div className="row">
            <button className="primary" onClick={save} disabled={action.busy || !name.trim()}>
              Simpan
            </button>
            <button onClick={() => setEditing(false)}>Batal</button>
          </div>
        </td>
      </tr>
    );
  }

  return (
    <tr>
      <td>
        <strong>{acronym.name}</strong>
      </td>
      <td>
        {acronym.description || <span className="muted">—</span>}
        <ErrorBanner message={action.error} />
      </td>
      <td>
        <div className="row">
          <button onClick={() => setEditing(true)}>Edit</button>
          <button className="danger" onClick={remove} disabled={action.busy}>
            Hapus
          </button>
        </div>
      </td>
    </tr>
  );
}
