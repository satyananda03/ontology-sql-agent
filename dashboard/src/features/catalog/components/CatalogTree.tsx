// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { Empty, Loading } from "@/components/ui";
import type { CatalogTree as Tree } from "../hooks/useCatalogTree";

interface CatalogTreeProps {
  tree: Tree;
  selectedId: string | null;
  onSelect: (tableId: string) => void;
}

const caret = (open: boolean): string => (open ? "▾" : "▸");

export function CatalogTree({ tree, selectedId, onSelect }: CatalogTreeProps) {
  const { source, tables, isOpen } = tree;
  return (
    <nav className="card" aria-label="Pohon katalog">
      {source.loading && <Loading />}
      {source.data === null && <Empty>Database belum di-ingest. Periksa log ingestion service.</Empty>}
      {source.data && (
        <>
          <div className="muted mono small" style={{ padding: "0 10px 8px" }}>
            {source.data.database.name}
          </div>
          {source.data.schemas.length === 0 && <Empty>Belum ada schema yang di-ingest.</Empty>}
          <ul className="tree">
            {source.data.schemas.map((schema) => (
              <li key={schema.id}>
                <button className="node" aria-expanded={isOpen(schema.id)} onClick={() => tree.toggleSchema(schema.id)}>
                  {caret(isOpen(schema.id))} {schema.schema_name}{" "}
                  <span className="muted">({schema.tables_count ?? 0})</span>
                </button>
                {isOpen(schema.id) && (
                  <ul className="tree">
                    {!tables[schema.id] && <li className="muted">Memuat…</li>}
                    {tables[schema.id]?.map((table) => (
                      <li key={table.id}>
                        <button
                          className={`node ${table.id === selectedId ? "selected" : ""}`}
                          onClick={() => onSelect(table.id)}
                        >
                          {table.name}
                          {table.description_certified && <span aria-label="certified"> ✓</span>}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </nav>
  );
}
