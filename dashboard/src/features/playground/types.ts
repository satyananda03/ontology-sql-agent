// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import type { S } from "@/types";

/** One question sent to the SQL agent and, once it answers, its result. */
export interface Turn {
  id: number;
  question: string;
  startedAt: number;
  seconds?: number;
  result?: S["SqlAgentResult"];
  error?: string;
}
