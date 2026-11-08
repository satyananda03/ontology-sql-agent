// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import type { ReactNode } from "react";

/** Page title, optionally followed by a one-paragraph description. */
export function PageHeader({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="page-head">
      <h1>{title}</h1>
      {children && <p className="muted">{children}</p>}
    </div>
  );
}
