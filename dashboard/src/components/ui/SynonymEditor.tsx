// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState, type FormEvent } from "react";

interface SynonymEditorProps {
  value: string[];
  busy?: boolean;
  /** The whole list after the change; the server trims it and drops duplicates. */
  onChange: (synonyms: string[]) => void;
}

/** A list of alternate names, kept by a person: remove one with ×, add with Enter. */
export function SynonymEditor({ value, busy, onChange }: SynonymEditorProps) {
  const [draft, setDraft] = useState("");

  function add(e: FormEvent) {
    e.preventDefault();
    const added = draft
      .split(",")
      .map((synonym) => synonym.trim())
      .filter(Boolean);
    if (!added.length) return;
    onChange([...value, ...added]);
    setDraft("");
  }

  return (
    <div className="stack tight">
      {!!value.length && (
        <div className="row">
          {value.map((synonym) => (
            <span key={synonym} className="badge neutral">
              {synonym}
              <button
                type="button"
                className="link"
                aria-label={`Hapus sinonim ${synonym}`}
                title="Hapus"
                disabled={busy}
                onClick={() => onChange(value.filter((other) => other !== synonym))}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}
      <form className="row" onSubmit={add}>
        <input
          className="narrow"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Tambah sinonim, pisahkan dengan koma"
          aria-label="Tambah sinonim"
        />
        <button disabled={busy || !draft.trim()}>Tambah</button>
      </form>
    </div>
  );
}
