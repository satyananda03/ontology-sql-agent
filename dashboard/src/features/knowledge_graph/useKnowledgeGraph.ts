// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useEffect } from "react";
import { useFetch } from "@/hooks/useFetch";
import { loadGraph } from "./graphKinds";
import { useKnowledgeGraphStore } from "./store";

/**
 * Load the combined term and table graph into the store.
 *
 * The graph lives in the zustand store rather than in this hook's state: the
 * viewer, the properties panel, the legend and the search all read it there.
 */
export function useKnowledgeGraph(databaseId: string) {
  const graph = useFetch(() => loadGraph(databaseId), [databaseId]);

  useEffect(() => {
    if (graph.data) useKnowledgeGraphStore.getState().setRawGraph(graph.data);
  }, [graph.data]);

  return { loading: graph.loading, error: graph.error, reload: graph.reload };
}
