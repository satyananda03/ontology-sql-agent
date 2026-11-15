// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState } from "react";
import { queryClient } from "@/lib/query-client";
import { Badge } from "./Badge";
import { BusyButton } from "./BusyButton";
import { Spinner } from "./Feedback";
import { toast } from "./Toaster";

// Certify writes run one at a time in click order, so a reviewer can click down a list without waiting.
let queueTail: Promise<unknown> = Promise.resolve();
let queued = 0;

function enqueueCertify<T>(write: () => Promise<T>): Promise<T> {
  queued++;
  const run = queueTail.then(write);
  queueTail = run
    .catch(() => undefined)
    .finally(() => {
      // Other pages show certification too: refresh them once the queue is empty, not per click.
      if (--queued === 0) void queryClient.invalidateQueries();
    });
  return run;
}

interface CertifyToggleProps {
  certified: boolean | null | undefined;
  /** What is certified, named in the failure toast: a column, an attribute, "nama term"... */
  name?: string | null;
  /** Saves the flag and updates the cached data; rejects when the save failed. */
  onChange: (certified: boolean) => Promise<unknown>;
}

/**
 * One control per item: a Certify button while pending; the badge and an undo once certified.
 * A click shows its outcome at once and saves through the queue; a failed save reverts and says so.
 */
export function CertifyToggle({ certified, name, onChange }: CertifyToggleProps) {
  // The flag being saved, shown in place of the stored one until the save ends.
  const [saving, setSaving] = useState<boolean>();
  const busy = saving !== undefined;

  async function save(value: boolean) {
    setSaving(value);
    try {
      await enqueueCertify(() => onChange(value));
      toast(value ? "Certified" : "Certify dibatalkan");
    } catch {
      toast([value ? "Certify" : "Batalkan certify", name, "gagal"].filter(Boolean).join(" "), "error");
    } finally {
      setSaving(undefined);
    }
  }

  return (saving ?? certified) ? (
    <div className="row certify">
      <Badge tone="success">
        {busy && <Spinner />}
        Certified
      </Badge>
      {!busy && (
        <button className="link small" onClick={() => save(false)}>
          Batalkan
        </button>
      )}
    </div>
  ) : (
    <BusyButton className="certify" busy={busy} onClick={() => save(true)}>
      Certify
    </BusyButton>
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
