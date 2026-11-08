// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useState, type DependencyList } from "react";

/**
 * Run *load* on mount and whenever *deps* change. `reload` runs it again,
 * `setData` patches the result locally after a successful write.
 */
export function useFetch<T>(load: () => Promise<T>, deps: DependencyList = []) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let live = true;
    setLoading(true);
    setError(undefined);
    load()
      .then((d) => live && setData(d))
      .catch((e: Error) => live && setError(e.message))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
    // Deliberately narrow deps: *deps* stands in for *load*.
  }, [...deps, tick]);

  return { data, error, loading, setData, reload: () => setTick((t) => t + 1) };
}
