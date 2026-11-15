// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useEffect } from "react";
import { useFetch } from "@/hooks/useFetch";
import { combinedGraphToRaw, MANUAL_SOURCE } from "./graph";
import { graphQuery } from "./graphKinds";
import { useKnowledgeGraphStore } from "./store";

/**
 * Load the combined term, table and SQL attribute graph into the store.
 *
 * The graph lives in the zustand store rather than in this hook's state: the
 * viewer, the properties panel, the legend and the search all read it there.
 * The SQL attribute filter rebuilds it from the cached sources, without a refetch.
 */
export function useKnowledgeGraph(databaseId: string) {
  const graph = useFetch(graphQuery(databaseId));
  const filter = useKnowledgeGraphStore((state) => state.sqlAttributeFilter);

  useEffect(() => {
    if (!graph.data) return;
    const { semantic, data, sqlAttributes } = graph.data;
    const shown =
      filter === "off" ? [] : filter === "manual" ? sqlAttributes.filter((a) => a.source === MANUAL_SOURCE) : sqlAttributes;
    useKnowledgeGraphStore.getState().setRawGraph(combinedGraphToRaw(semantic, data, shown));
  }, [graph.data, filter]);

  return { loading: graph.loading, error: graph.error, reload: graph.reload };
}
