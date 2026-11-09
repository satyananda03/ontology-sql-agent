// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState } from "react";
import { Badge } from "./Badge";

interface CertifyToggleProps {
  certified: boolean | null | undefined;
  onChange: (certified: boolean) => void;
  disabled?: boolean;
}

/** One control per item: a Certify button while pending; the badge and an undo once certified. */
export function CertifyToggle({ certified, onChange, disabled }: CertifyToggleProps) {
  return certified ? (
    <div className="row certify">
      <Badge tone="success">Certified</Badge>
      <button className="link small" disabled={disabled} onClick={() => onChange(false)}>
        Batalkan
      </button>
    </div>
  ) : (
    <button className="certify" disabled={disabled} onClick={() => onChange(true)}>
      Certify
    </button>
  );
}

/**
 * Whether an edit should save as certified. Changing the text drops it to unchecked —
 * a certificate vouches for the text someone reviewed — unless the reviewer ticks it again.
 * Returns `[checked, setChecked, patch]`; `patch` is the flag to send, or undefined when unchanged.
 */
export function useCertifyChoice(certified: boolean, changed: boolean) {
  const [choice, setChoice] = useState<boolean>();
  const checked = choice ?? (certified && !changed);
  const patch = checked !== certified ? checked : undefined;
  return { checked, setChecked: setChoice, reset: () => setChoice(undefined), patch };
}

interface CertifyChoiceProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  /** The saved state, to explain why the box went unchecked. */
  certified: boolean;
  disabled?: boolean;
}

/** The certify checkbox shown next to Simpan while text is being edited. */
export function CertifyChoice({ checked, onChange, certified, disabled }: CertifyChoiceProps) {
  return (
    <div className="stack tight">
      <label className="check">
        <input type="checkbox" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
        Certify: isi ini sudah saya periksa dan benar
      </label>
      {certified && !checked && (
        <div className="muted small">Isi berubah, jadi statusnya kembali ke Pending saat disimpan.</div>
      )}
    </div>
  );
}
