// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import type { ReactNode } from "react";

export type BadgeTone = "neutral" | "success" | "info" | "warning" | "error";

export function Badge({ tone = "neutral", children }: { tone?: BadgeTone; children: ReactNode }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

/** Review state of one field (boolean) or a term rolled up (string). */
export function CertBadge({ value }: { value: boolean | string | null | undefined }) {
  const state = value === true ? "certified" : value === false || value == null ? "pending" : value;
  if (state === "certified") return <Badge tone="success">Certified</Badge>;
  if (state === "partial") return <Badge tone="info">Partial</Badge>;
  return <Badge tone="warning">Pending</Badge>;
}
