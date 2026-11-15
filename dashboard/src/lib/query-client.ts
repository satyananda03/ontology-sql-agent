// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { QueryClient } from "@tanstack/react-query";

/**
 * One cache for the whole app: two components asking for the same key share
 * one request, and a page opened again shows its last data at once while it
 * refreshes in the background. Queries are defined per feature, next to their
 * fetchers, as `<feature>Queries` in `features/<feature>/api.ts`.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Fresh for 30 s: navigating back and forth does not refetch. Writes
      // through `useAction` mark everything stale, so edits still show.
      staleTime: 30_000,
      // Once, not three times: a failing backend should not get a burst.
      retry: 1,
    },
  },
});
