// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { type ReactNode, useEffect, useRef, useState } from "react";
import { CertifyChoice, useCertifyChoice } from "./Certify";
import { ErrorBanner } from "./Feedback";

interface TextDialogProps {
  title: ReactNode;
  /** Context shown above the text box, e.g. what the text describes. */
  children?: ReactNode;
  value: string | null | undefined;
  /** `certified` is the flag to send with the text, or undefined to leave it as is. */
  onSave: (value: string, certified?: boolean) => void;
  onClose: () => void;
  busy?: boolean;
  error?: string;
  /** The text's saved certify state; when given, editing offers to certify the new text. */
  certified?: boolean;
}

/** A modal text editor that covers the page, so a long text has room. Esc or Batal closes it. */
export function TextDialog({ title, children, value, onSave, onClose, busy, error, certified }: TextDialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const [draft, setDraft] = useState(value ?? "");
  const changed = draft !== (value ?? "");
  const certify = useCertifyChoice(!!certified, changed);
  useEffect(() => ref.current?.showModal(), []);

  return (
    <dialog ref={ref} className="text-dialog" onClose={onClose}>
      <div className="stack">
        <h2>{title}</h2>
        {children}
        <textarea rows={10} value={draft} autoFocus onChange={(e) => setDraft(e.target.value)} />
        {changed && certified !== undefined && (
          <CertifyChoice checked={certify.checked} onChange={certify.setChecked} certified={certified} disabled={busy} />
        )}
        <ErrorBanner message={error} />
        <div className="row">
          <button className="primary" disabled={busy || !changed} onClick={() => onSave(draft, certify.patch)}>
            Simpan
          </button>
          <button disabled={busy} onClick={() => ref.current?.close()}>
            Batal
          </button>
        </div>
      </div>
    </dialog>
  );
}
