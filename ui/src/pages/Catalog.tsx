// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, useFetch, type S } from "../api";
import { CertBadge, CertifyCheck, Empty, ErrorBanner, Loading, PageHead, TextEditor, useAction } from "../ui";

type Table = S["TableSummary"];

export default function Catalog() {
  const [params, setParams] = useSearchParams();
  const tableId = params.get("table");
  const dbs = useFetch<S["ListResponse_DatabaseSummary_"]>("/datasources/dbs");
  const [schemas, setSchemas] = useState<Record<string, S["SchemaSummary"][]>>({});
  const [tables, setTables] = useState<Record<string, Table[]>>({});
  const [open, setOpen] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string>();

  const toggle = (id: string, isOpen: boolean) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (isOpen) next.add(id);
      else next.delete(id);
      return next;
    });

  async function loadSchemas(dbId: string) {
    if (schemas[dbId]) return schemas[dbId];
    const payload = await api<S["SchemasPayload"] | null>(`/schemas/${dbId}`);
    const list = payload?.schemas ?? [];
    setSchemas((prev) => ({ ...prev, [dbId]: list }));
    return list;
  }

  async function loadTables(schemaId: string, dbName: string) {
    if (tables[schemaId]) return tables[schemaId];
    const response = await api<S["ListResponse_TableSummary_"]>(
      `/tables/${schemaId}?database_name=${encodeURIComponent(dbName)}`,
    );
    setTables((prev) => ({ ...prev, [schemaId]: response.data }));
    return response.data;
  }

  const expand = (id: string, load: () => Promise<unknown>) => {
    const willOpen = !open.has(id);
    toggle(id, willOpen);
    if (willOpen) load().catch((e: Error) => setError(e.message));
  };

  // A link straight to a table (from a Term or a search hit): find its
  // database and schema by name, then open the tree down to it.
  useEffect(() => {
    if (!tableId || !dbs.data) return;
    if (Object.values(tables).some((list) => list.some((t) => t.id === tableId))) return;
    (async () => {
      const page = await api<S["ObjectPageResponse_TableColumns_"]>(`/columns/${tableId}?limit=1`);
      const db = dbs.data!.data.find((d) => d.name === page.data.database_name);
      if (!db) return;
      const schema = (await loadSchemas(db.id)).find((s) => s.schema_name === page.data.schema_name);
      if (!schema) return;
      await loadTables(schema.id, db.name ?? "");
      setOpen((prev) => new Set([...prev, db.id, schema.id]));
    })().catch((e: Error) => setError(e.message));
  }, [tableId, dbs.data]);

  const selected = Object.values(tables)
    .flat()
    .find((t) => t.id === tableId);
  const updateTable = (table: Table) =>
    setTables((prev) =>
      Object.fromEntries(
        Object.entries(prev).map(([k, list]) => [k, list.map((t) => (t.id === table.id ? table : t))]),
      ),
    );

  return (
    <>
      <PageHead title="Katalog">
        Database, skema, tabel, dan kolom yang di-ingest. Deskripsi yang di-certify dipakai agent saat memilih
        tabel dan kolom.
      </PageHead>
      <ErrorBanner message={dbs.error ?? error} />
      <div className="grid2">
        <nav className="card" aria-label="Pohon katalog">
          {dbs.loading && <Loading />}
          {dbs.data?.data.length === 0 && <Empty>Belum ada database. Tambahkan koneksi dulu.</Empty>}
          <ul className="tree">
            {dbs.data?.data.map((db) => (
              <li key={db.id}>
                <button className="node" aria-expanded={open.has(db.id)} onClick={() => expand(db.id, () => loadSchemas(db.id))}>
                  {open.has(db.id) ? "▾" : "▸"} {db.name}
                </button>
                {open.has(db.id) && (
                  <ul className="tree">
                    {!schemas[db.id] && <li className="muted">Memuat…</li>}
                    {schemas[db.id]?.map((schema) => (
                      <li key={schema.id}>
                        <button
                          className="node"
                          aria-expanded={open.has(schema.id)}
                          onClick={() => expand(schema.id, () => loadTables(schema.id, db.name ?? ""))}
                        >
                          {open.has(schema.id) ? "▾" : "▸"} {schema.schema_name}{" "}
                          <span className="muted">({schema.tables_count ?? 0})</span>
                        </button>
                        {open.has(schema.id) && (
                          <ul className="tree">
                            {!tables[schema.id] && <li className="muted">Memuat…</li>}
                            {tables[schema.id]?.map((table) => (
                              <li key={table.id}>
                                <button
                                  className={`node ${table.id === tableId ? "selected" : ""}`}
                                  onClick={() => setParams({ table: table.id })}
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
                )}
              </li>
            ))}
          </ul>
        </nav>
        <div>
          {selected ? (
            <TablePanel key={selected.id} table={selected} onChange={updateTable} />
          ) : tableId ? (
            <Loading />
          ) : (
            <Empty>Pilih tabel di sebelah kiri untuk me-review deskripsinya.</Empty>
          )}
        </div>
      </div>
    </>
  );
}

function TablePanel({ table, onChange }: { table: Table; onChange: (t: Table) => void }) {
  const columns = useFetch<S["ObjectPageResponse_TableColumns_"]>(`/columns/${table.id}`);
  const action = useAction();

  async function patchNode<T extends { id: string }>(node: T, body: S["NodeUpdate"]): Promise<T | undefined> {
    const saved = await action.run(
      () => api<S["NodeUpdateResult"] | null>(`/nodes/${node.id}`, { method: "PATCH", json: body }),
      "Tersimpan",
    );
    return saved ? { ...node, description: saved.description, description_certified: saved.description_certified } : undefined;
  }

  async function patchColumn(column: S["ColumnSummary"], body: S["NodeUpdate"]) {
    const saved = await patchNode(column, body);
    if (!saved || !columns.data) return;
    const list = columns.data.data.columns ?? [];
    columns.setData({
      ...columns.data,
      data: { ...columns.data.data, columns: list.map((c) => (c.id === saved.id ? saved : c)) },
    });
  }

  return (
    <>
      <div className="card stack">
        <div className="row spread">
          <div>
            <div className="muted mono">
              {table.database_name}.{table.schema_name}
            </div>
            <h2 style={{ margin: 0 }}>{table.name}</h2>
          </div>
          <div className="row">
            <CertBadge value={table.description_certified} />
            <CertifyCheck
              label="Certify deskripsi"
              checked={table.description_certified}
              disabled={action.busy}
              onChange={async (v) => {
                const saved = await patchNode(table, { description_certified: v });
                if (saved) onChange(saved);
              }}
            />
          </div>
        </div>
        <TextEditor
          value={table.description}
          rows={3}
          busy={action.busy}
          placeholder="Belum ada deskripsi."
          onSave={async (description) => {
            const saved = await patchNode(table, { description });
            if (saved) onChange(saved);
          }}
        />
        <ErrorBanner message={action.error} />
      </div>
      <section className="card">
        <h2>Kolom {columns.data && <span className="muted">({columns.data.total})</span>}</h2>
        <ErrorBanner message={columns.error} />
        {columns.loading && !columns.data && <Loading />}
        {columns.data && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Kolom</th>
                  <th style={{ width: "50%" }}>Deskripsi</th>
                  <th>Review</th>
                </tr>
              </thead>
              <tbody>
                {columns.data.data.columns?.map((column) => (
                  <tr key={column.id}>
                    <td>
                      <strong className="mono">{column.column_name}</strong>
                      <div className="muted mono">{column.data_type}</div>
                      {!!column.sample_values?.length && (
                        <div className="muted" style={{ fontSize: 12 }}>
                          contoh: {column.sample_values.slice(0, 5).join(", ")}
                        </div>
                      )}
                    </td>
                    <td>
                      <TextEditor
                        value={column.description}
                        rows={2}
                        busy={action.busy}
                        onSave={(description) => patchColumn(column, { description })}
                      />
                    </td>
                    <td>
                      <div className="stack" style={{ gap: 6 }}>
                        <CertBadge value={column.description_certified} />
                        <CertifyCheck
                          label="Certify"
                          checked={column.description_certified}
                          disabled={action.busy}
                          onChange={(v) => patchColumn(column, { description_certified: v })}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
