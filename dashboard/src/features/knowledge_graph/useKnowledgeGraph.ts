// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useEffect } from "react";
import { useFetch } from "@/hooks/useFetch";
import { GRAPH_KINDS } from "./graphKinds";
import { useKnowledgeGraphStore } from "./store";

/**
 * Load the graph for the active tab into the store.
 *
 * The graph lives in the zustand store rather than in this hook's state: the
 * viewer, the properties panel, the legend and the search all read it there.
 */
export function useKnowledgeGraph(databaseId: string) {
  const kind = useKnowledgeGraphStore((state) => state.kind);
  const includeSqlEdges = useKnowledgeGraphStore((state) => state.includeSqlEdges);
  const graph = useFetch(
    () => GRAPH_KINDS[kind].load(databaseId, { includeSqlEdges }),
    [kind, databaseId, includeSqlEdges],
  );

  useEffect(() => {
    if (graph.data) useKnowledgeGraphStore.getState().setRawGraph(graph.data);
  }, [graph.data]);

  return { loading: graph.loading, error: graph.error, reload: graph.reload };
}
