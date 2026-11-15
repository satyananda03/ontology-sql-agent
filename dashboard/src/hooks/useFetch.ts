// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useQuery, useQueryClient, type QueryKey, type UseQueryOptions } from "@tanstack/react-query";

/**
 * `useQuery` in the shape the pages use: pass a `<feature>Queries.x()` from
 * the feature's api.ts (spread it to add e.g. `refetchInterval`). `setData`
 * patches the cached result after a successful write, `reload` refetches.
 */
export function useFetch<T, K extends QueryKey>(options: UseQueryOptions<T, Error, T, K>) {
  const client = useQueryClient();
  const query = useQuery(options);
  return {
    data: query.data,
    error: query.error?.message,
    // First load only: a background refresh keeps showing the cached data.
    loading: query.isLoading,
    setData: (data: T) => client.setQueryData<T>(options.queryKey as QueryKey, data),
    reload: () => void query.refetch(),
  };
}
