// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import type { ReactNode } from "react";

export function ErrorBanner({ message }: { message?: string }) {
  return message ? (
    <div className="banner" role="alert">
      {message}
    </div>
  ) : null;
}

export function Spinner() {
  return <span className="spinner" aria-hidden="true" />;
}

export function Loading({ label = "Memuat…" }: { label?: string }) {
  return (
    <div className="row muted" role="status">
      <Spinner /> {label}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>;
}
