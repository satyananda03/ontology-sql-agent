// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useQuery, useQueryClient, type QueryKey, type UseQueryOptions } from "@tanstack/react-query";

/**
 * `useQuery` in the shape the pages use: pass a `<feature>Queries.x()` from
 * the feature's api.ts (spread it to add e.g. `refetchInterval`). `setData`
 * patches the cached result after a successful write, `reload` refetches.
 *
 * Pass `setData` an updater when writes can overlap: it reads the cache as it
 * is now, where a value built from `data` would undo a write that landed since.
 */
export function useFetch<T, K extends QueryKey>(options: UseQueryOptions<T, Error, T, K>) {
  const client = useQueryClient();
  const query = useQuery(options);
  return {
    data: query.data,
    error: query.error?.message,
    // First load only: a background refresh keeps showing the cached data.
    loading: query.isLoading,
    setData: (next: T | ((current: T) => T)) =>
      client.setQueryData<T>(options.queryKey as QueryKey, (current) =>
        typeof next !== "function" ? next : current === undefined ? current : (next as (current: T) => T)(current),
      ),
    // Resolves once the fresh data is in, for a caller that reads it next.
    reload: () => query.refetch(),
  };
}
