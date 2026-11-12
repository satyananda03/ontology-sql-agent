// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { api } from "@/lib/api-client";
import type { S } from "@/types";

/** Ask the agent exactly as an MCP caller would. */
export function querySqlAgent(question: string): Promise<S["SqlAgentResult"]> {
  return api("/sql-agent/query", { method: "POST", json: { question } });
}
