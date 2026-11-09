// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useState } from "react";
import { CertifyChoice, useCertifyChoice } from "./Certify";

interface TextEditorProps {
  value: string | null | undefined;
  /** `certified` is the flag to send with the text, or undefined to leave it as is. */
  onSave: (value: string, certified?: boolean) => void;
  busy?: boolean;
  mono?: boolean;
  rows?: number;
  placeholder?: string;
  /** The text's saved certify state; when given, editing offers to certify the new text. */
  certified?: boolean;
}

/** A text area that saves on demand; Save shows only once the text changed. */
export function TextEditor({ value, onSave, busy, mono, rows = 3, placeholder, certified }: TextEditorProps) {
  const saved = value ?? "";
  const [draft, setDraft] = useState(saved);
  const certify = useCertifyChoice(!!certified, draft !== saved);
  useEffect(() => {
    setDraft(saved);
    certify.reset();
  }, [saved]); // reset only when the saved text changes

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
        <>
          {certified !== undefined && (
            <CertifyChoice
              checked={certify.checked}
              onChange={certify.setChecked}
              certified={certified}
              disabled={busy}
            />
          )}
          <div className="row">
            <button className="primary" disabled={busy} onClick={() => onSave(draft, certify.patch)}>
              Simpan
            </button>
            <button
              disabled={busy}
              onClick={() => {
                setDraft(saved);
                certify.reset();
              }}
            >
              Batal
            </button>
          </div>
        </>
      )}
    </div>
  );
}
