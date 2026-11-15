// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState } from "react";
import { BusyButton, ErrorBanner } from "@/components/ui";
import { useAction } from "@/hooks/useAction";
import type { S } from "@/types";
import { deleteGlossaryEntry, updateGlossaryEntry } from "../api";

/** One glossary entry, editable in place. */
export function GlossaryRow({ entry, onChange }: { entry: S["GlossaryEntry"]; onChange: () => void }) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(entry.name);
  const [description, setDescription] = useState(entry.description);
  const action = useAction();

  async function save() {
    const saved = await action.run(() => updateGlossaryEntry(entry.id, { name, description }), "Tersimpan");
    if (!saved) return;
    setEditing(false);
    onChange();
  }

  async function remove() {
    if (!window.confirm(`Hapus “${entry.name}” dari glossary?`)) return;
    const done = await action.run(() => deleteGlossaryEntry(entry.id), "Dihapus");
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
            <BusyButton className="primary" onClick={save} busy={action.busy} disabled={!name.trim()}>
              Simpan
            </BusyButton>
            <button onClick={() => setEditing(false)}>Batal</button>
          </div>
        </td>
      </tr>
    );
  }

  return (
    <tr>
      <td>
        <strong>{entry.name}</strong>
      </td>
      <td>
        {entry.description || <span className="muted">—</span>}
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
