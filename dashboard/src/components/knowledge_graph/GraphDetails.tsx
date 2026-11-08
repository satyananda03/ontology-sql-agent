// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

// Drill-down sections of the properties panel, one per node or edge kind.
// GRAPH_KINDS picks which one a tab shows.

import type { ReactNode } from "react";
import { getTableColumns } from "@/features/catalog/api";
import { getTableDetails, getTermPath, getTermTables } from "@/features/knowledge_graph/api";
import type { RawEdge } from "@/features/knowledge_graph/types";
import { useFetch } from "@/hooks/useFetch";
import { truncate } from "@/lib/utils";

const SQL_PREVIEW_LENGTH = 160;

export function TermDetails({ nodeId }: { nodeId: string }) {
  const details = useFetch(() => getTermTables(nodeId), [nodeId]);
  return (
    <Section title="Tabel" state={details}>
      {details.data?.tables?.map((table) => (
        <Item key={table.id}>{qualified(table.schema_name, table.name)}</Item>
      ))}
    </Section>
  );
}

export function TableDetails({ nodeId }: { nodeId: string }) {
  const columns = useFetch(() => getTableColumns(nodeId), [nodeId]);
  const details = useFetch(() => getTableDetails(nodeId), [nodeId]);
  return (
    <>
      <Section title="Kolom" state={columns}>
        {columns.data?.data.columns?.map((column) => (
          <Item key={column.id}>
            {column.column_name} <span className="text-neutral-500">{column.data_type}</span>
          </Item>
        ))}
      </Section>
      <Section title="Term" state={details}>
        {details.data?.terms?.map((term) => <Item key={term.id}>{term.name}</Item>)}
      </Section>
      <Section title="Query SQL" state={details}>
        {details.data?.queries?.map((query) => (
          <Item key={query.id}>{truncate(query.sql, SQL_PREVIEW_LENGTH)}</Item>
        ))}
      </Section>
    </>
  );
}

/** The real chain behind a term-to-term edge: term, table, column, attribute, term. */
export function TermPathDetails({ edge }: { edge: RawEdge }) {
  const path = useFetch(() => getTermPath(edge.source, edge.target), [edge.source, edge.target]);
  const hops = path.data?.hops ?? [];
  return (
    <Section title="Rantai relasi" state={path}>
      {hops.length > 0 && <Item>{pathNodeLabel(hops[0].source)}</Item>}
      {hops.map((hop, index) => (
        <div key={index}>
          <div className="py-0.5 pl-2.5 text-[10px] text-[#00E676]">↓ {hop.relationship}</div>
          <Item>{pathNodeLabel(hop.target)}</Item>
        </div>
      ))}
    </Section>
  );
}

/** The key columns and stored queries behind a table-to-table edge; already in the graph data. */
export function ForeignKeyDetails({ edge }: { edge: RawEdge }) {
  return (
    <>
      <Section title="Foreign key">
        {edge.foreignKeys.map((key, index) => (
          <Item key={index}>
            {key.source_column} → {key.target_column}
          </Item>
        ))}
      </Section>
      <Section title="Query SQL">
        {edge.queries.map((query, index) => (
          <Item key={index}>{truncate(query, SQL_PREVIEW_LENGTH)}</Item>
        ))}
      </Section>
    </>
  );
}

interface FetchState {
  loading: boolean;
  error?: string;
}

/** A titled list; shows the fetch state while it has none, and "Tidak ada" when empty. */
function Section({ title, state, children }: { title: string; state?: FetchState; children?: ReactNode[] }) {
  const items = (children ?? []).flat().filter(Boolean);
  let body: ReactNode = items;
  if (state?.error) body = <p className="text-[11px] text-[#FF5858]">{state.error}</p>;
  else if (state?.loading && items.length === 0) body = <p className="text-[11px] text-neutral-500">Memuat…</p>;
  else if (items.length === 0) body = <p className="text-[11px] text-neutral-500">Tidak ada.</p>;
  return (
    <div className="mb-4">
      <h4 className="mb-2.5 text-xs font-bold uppercase tracking-wider text-[#00E5FF]">{title}</h4>
      <div className="max-h-48 space-y-1 overflow-y-auto pr-1">{body}</div>
    </div>
  );
}

function Item({ children }: { children: ReactNode }) {
  return (
    <div className="break-words rounded border border-[#2A2A2A] bg-[#1C1C1C] px-2.5 py-1.5 text-[11px] text-neutral-300">
      {children}
    </div>
  );
}

const qualified = (schema: string | null | undefined, name: string | null | undefined): string =>
  [schema, name].filter(Boolean).join(".");

function pathNodeLabel(node: { type: string; name?: string | null; table_name?: string | null }): ReactNode {
  const name = node.table_name && node.type === "column" ? qualified(node.table_name, node.name) : node.name;
  return (
    <>
      <span className="mr-1.5 text-neutral-500">{node.type}</span>
      {name}
    </>
  );
}
