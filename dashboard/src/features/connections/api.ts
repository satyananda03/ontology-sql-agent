// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { api } from "@/lib/api-client";
import type { S } from "@/types";

/** The one source database, from `CONNECTION_STRINGS` in .env. */
export function getConnection(): Promise<S["SourceConnection"]> {
  return api("/connection");
}
