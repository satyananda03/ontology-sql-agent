// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useState } from "react";

interface TextEditorProps {
  value: string | null | undefined;
  onSave: (value: string) => void;
  busy?: boolean;
  mono?: boolean;
  rows?: number;
  placeholder?: string;
}

/** A text area that saves on demand; Save shows only once the text changed. */
export function TextEditor({ value, onSave, busy, mono, rows = 3, placeholder }: TextEditorProps) {
  const saved = value ?? "";
  const [draft, setDraft] = useState(saved);
  useEffect(() => setDraft(saved), [saved]);

  return (
    <div className="stack tight">
      <textarea
        className={mono ? "mono" : undefined}
        rows={rows}
        value={draft}
        placeholder={placeholder}
        onChange={(e) => setDraft(e.target.value)}
      />
      {draft !== saved && (
        <div className="row">
          <button className="primary" disabled={busy} onClick={() => onSave(draft)}>
            Simpan
          </button>
          <button disabled={busy} onClick={() => setDraft(saved)}>
            Batal
          </button>
        </div>
      )}
    </div>
  );
}
