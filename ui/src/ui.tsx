// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useState, type ReactNode } from "react";

type Tone = "solid" | "outline" | "alert" | "alert-solid";

export function Badge({ tone = "outline", children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

/** Review state of one field (boolean) or a term rolled up (string). */
export function CertBadge({ value }: { value: boolean | string | null | undefined }) {
  const state = value === true ? "certified" : value === false || value == null ? "pending" : value;
  if (state === "certified") return <Badge tone="solid">Certified</Badge>;
  if (state === "partial") return <Badge>Partial</Badge>;
  return <Badge tone="alert">Pending</Badge>;
}

export function ErrorBanner({ message }: { message?: string }) {
  return message ? <div className="banner" role="alert">{message}</div> : null;
}

export function Loading({ label = "Memuat…" }: { label?: string }) {
  return (
    <div className="row muted" role="status">
      <span className="spinner" /> {label}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>;
}

export function PageHead({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="page-head">
      <h1>{title}</h1>
      {children && <p className="muted">{children}</p>}
    </div>
  );
}

// One toast at a time, raised from anywhere without a context provider.
export function toast(message: string): void {
  window.dispatchEvent(new CustomEvent("toast", { detail: message }));
}

export function Toaster() {
  const [message, setMessage] = useState<string>();
  useEffect(() => {
    let timer: number | undefined;
    const show = (e: Event) => {
      setMessage((e as CustomEvent<string>).detail);
      window.clearTimeout(timer);
      timer = window.setTimeout(() => setMessage(undefined), 2500);
    };
    window.addEventListener("toast", show);
    return () => window.removeEventListener("toast", show);
  }, []);
  return message ? <div className="toast" role="status">{message}</div> : null;
}

/**
 * Run one async action at a time: tracks `busy`, keeps the last error for a
 * banner, and toasts *done* on success. Returns the action's result, or
 * undefined when it failed.
 */
export function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  async function run<T>(action: () => Promise<T>, done?: string): Promise<T | undefined> {
    setBusy(true);
    setError(undefined);
    try {
      const result = await action();
      if (done) toast(done);
      return result;
    } catch (e) {
      setError((e as Error).message);
      return undefined;
    } finally {
      setBusy(false);
    }
  }
  return { busy, error, setError, run };
}

export function CertifyCheck({
  checked,
  onChange,
  disabled,
  label = "Certified",
}: {
  checked: boolean | null | undefined;
  onChange: (value: boolean) => void;
  disabled?: boolean;
  label?: string;
}) {
  return (
    <label className="check">
      <input
        type="checkbox"
        checked={!!checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      {label}
    </label>
  );
}

/** A text area that saves on demand; Save is enabled only once the text changed. */
export function TextEditor({
  value,
  onSave,
  busy,
  mono,
  rows = 3,
  placeholder,
}: {
  value: string | null | undefined;
  onSave: (value: string) => void;
  busy?: boolean;
  mono?: boolean;
  rows?: number;
  placeholder?: string;
}) {
  const [draft, setDraft] = useState(value ?? "");
  useEffect(() => {
    setDraft(value ?? "");
  }, [value]);
  const dirty = draft !== (value ?? "");
  return (
    <div className="stack" style={{ gap: 6 }}>
      <textarea
        className={mono ? "mono" : undefined}
        rows={rows}
        value={draft}
        placeholder={placeholder}
        onChange={(e) => setDraft(e.target.value)}
      />
      {dirty && (
        <div className="row">
          <button className="primary" disabled={busy} onClick={() => onSave(draft)}>
            Simpan
          </button>
          <button disabled={busy} onClick={() => setDraft(value ?? "")}>
            Batal
          </button>
        </div>
      )}
    </div>
  );
}
