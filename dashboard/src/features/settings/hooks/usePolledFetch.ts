// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useEffect } from "react";
import { useFetch } from "@/hooks/useFetch";

const POLL_MS = 5000;

/**
 * `useFetch`, repeated while the page is open so a running job shows when it
 * finishes. Each poll waits for the previous answer: a slow ingestion service
 * must not pile requests up behind it.
 */
export function usePolledFetch<T>(load: () => Promise<T>) {
  const result = useFetch(load);
  useEffect(() => {
    if (result.loading) return;
    const timer = window.setTimeout(result.reload, POLL_MS);
    return () => window.clearTimeout(timer);
    // Deliberately narrow deps: re-arm only after each answer.
  }, [result.loading]);
  return result;
}
