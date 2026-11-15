// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { type CSSProperties, useEffect, useState } from "react";
import { CircleAlert, CircleCheck } from "lucide-react";

export type ToastTone = "success" | "error";

interface ToastMessage {
  id: number;
  message: string;
  tone: ToastTone;
}

const TOAST_EVENT = "toast";
const TOAST_MS = 3000;
const ICON = { success: CircleCheck, error: CircleAlert };

/** Show *message* briefly. One toast at a time, raised from anywhere without a provider. */
export function toast(message: string, tone: ToastTone = "success"): void {
  window.dispatchEvent(new CustomEvent(TOAST_EVENT, { detail: { message, tone } }));
}

/** Mounted once in the app layout: shows the latest toast, with a bar counting down to its dismissal. */
export function Toaster() {
  const [current, setCurrent] = useState<ToastMessage>();

  useEffect(() => {
    let timer: number | undefined;
    let nextId = 0;
    const show = (e: Event) => {
      const { message, tone } = (e as CustomEvent<Omit<ToastMessage, "id">>).detail;
      setCurrent({ id: ++nextId, message, tone });
      window.clearTimeout(timer);
      timer = window.setTimeout(() => setCurrent(undefined), TOAST_MS);
    };
    window.addEventListener(TOAST_EVENT, show);
    return () => {
      window.removeEventListener(TOAST_EVENT, show);
      window.clearTimeout(timer);
    };
  }, []);

  const Icon = current && ICON[current.tone];
  return (
    // Always mounted, so screen readers announce what appears in it.
    <div className="toaster" aria-live="polite">
      {current && Icon && (
        <div
          // A new id restarts the entry and countdown animations for a toast that replaces another.
          key={current.id}
          className={`toast tone-${current.tone}`}
          role={current.tone === "error" ? "alert" : undefined}
          style={{ "--toast-ms": `${TOAST_MS}ms` } as CSSProperties}
        >
          <span className="toast-icon" aria-hidden="true">
            <Icon size={18} />
          </span>
          {current.message}
        </div>
      )}
    </div>
  );
}
