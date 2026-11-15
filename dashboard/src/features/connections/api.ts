// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { S } from "@/types";

/** The one source database, from `CLIENT_DATABASE` in .env. */
export function getConnection(): Promise<S["SourceConnection"]> {
  return api("/connection");
}

export const connectionQueries = {
  current: () => queryOptions({ queryKey: ["connection"], queryFn: getConnection }),
};
