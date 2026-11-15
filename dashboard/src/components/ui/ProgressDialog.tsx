// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { type KeyboardEvent, type ReactNode, type SyntheticEvent, useEffect, useId, useRef } from "react";

export type ProgressStatus = "running" | "success" | "error";

interface ProgressDialogProps {
  open: boolean;
  title: ReactNode;
  status: ProgressStatus;
  /** What is happening, or how it ended; the caller words it per status. */
  children?: ReactNode;
  /** Called once the job has ended and the user closes the dialog (button or Esc). */
  onClose: () => void;
}

const ICON: Record<ProgressStatus, ReactNode> = {
  running: <span className="progress-ring" />,
  success: "✓",
  error: "!",
};

/** A modal for a long server job: status and an indeterminate bar. It cannot be closed while the job runs. */
export function ProgressDialog({ open, title, status, children, onClose }: ProgressDialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const running = status === "running";

  useEffect(() => {
    const dialog = ref.current;
    if (open && !dialog?.open) dialog?.showModal();
    if (!open && dialog?.open) dialog.close();
  }, [open]);

  // While running, neither a close request (Esc, Android back) nor Esc itself closes the dialog.
  // Esc is blocked on keydown too: Chrome lets a repeated Esc through despite a cancelled `cancel`.
  const blockCancel = (e: SyntheticEvent) => {
    if (running) e.preventDefault();
  };
  const blockEscape = (e: KeyboardEvent) => {
    if (running && e.key === "Escape") e.preventDefault();
  };

  return (
    <dialog
      ref={ref}
      className="progress-dialog"
      aria-labelledby={titleId}
      aria-busy={running}
      onCancel={blockCancel}
      onKeyDown={blockEscape}
      onClose={onClose}
    >
      <div className="stack">
        <div className={`progress-icon tone-${status}`} aria-hidden="true">
          {ICON[status]}
        </div>
        <h2 id={titleId}>{title}</h2>
        {/* Polite live region: a screen reader hears the outcome when it changes. */}
        <div className="muted" role="status">
          {children}
        </div>
        {running && <div className="progress-bar" role="progressbar" aria-label="Sedang berjalan" />}
        {!running && (
          <div className="row progress-actions">
            <button className="primary" onClick={() => ref.current?.close()} autoFocus>
              Tutup
            </button>
          </div>
        )}
      </div>
    </dialog>
  );
}

