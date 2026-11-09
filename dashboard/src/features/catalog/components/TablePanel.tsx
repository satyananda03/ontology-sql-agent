// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState } from "react";
import { CertifyToggle, ErrorBanner, Loading, TextDialog, TextEditor } from "@/components/ui";
import { useAction } from "@/hooks/useAction";
import { useFetch } from "@/hooks/useFetch";
import { replaceById } from "@/lib/utils";
import type { S } from "@/types";
import { getTableColumns, updateNode } from "../api";

type Table = S["TableSummary"];

interface TablePanelProps {
  table: Table;
  onChange: (table: Table) => void;
}

/** Review one table's description and the descriptions of its columns. */
export function TablePanel({ table, onChange }: TablePanelProps) {
  const columns = useFetch(() => getTableColumns(table.id), [table.id]);
  const action = useAction();
  const [editing, setEditing] = useState<S["ColumnSummary"]>();

  async function patchNode<T extends { id: string }>(node: T, body: S["NodeUpdate"]): Promise<T | undefined> {
    const saved = await action.run(() => updateNode(node.id, body), "Tersimpan");
    // The response echoes only the properties sent, so keep the node's others.
    return saved ? { ...node, ...saved } : undefined;
  }

  async function patchTable(body: S["NodeUpdate"]) {
    const saved = await patchNode(table, body);
    if (saved) onChange(saved);
  }

  async function patchColumn(column: S["ColumnSummary"], body: S["NodeUpdate"]) {
    const saved = await patchNode(column, body);
    if (!saved || !columns.data) return false;
    const data = columns.data.data;
    columns.setData({ ...columns.data, data: { ...data, columns: replaceById(data.columns ?? [], saved) } });
    return true;
  }

  async function saveColumnDescription(description: string, description_certified?: boolean) {
    if (editing && (await patchColumn(editing, { description, description_certified }))) setEditing(undefined);
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
          <CertifyToggle
            certified={table.description_certified}
            disabled={action.busy}
            onChange={(v) => patchTable({ description_certified: v })}
          />
        </div>
        <TextEditor
          value={table.description}
          rows={3}
          busy={action.busy}
          placeholder="Belum ada deskripsi."
          certified={!!table.description_certified}
          onSave={(description, description_certified) => patchTable({ description, description_certified })}
        />
        <ErrorBanner message={editing ? undefined : action.error} />
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
                        <div className="muted small">contoh: {column.sample_values.slice(0, 5).join(", ")}</div>
                      )}
                    </td>
                    <td>
                      <div className="stack tight">
                        <div className={column.description ? "clamp" : "muted"}>
                          {column.description || "Belum ada deskripsi."}
                        </div>
                        <button
                          className="link small"
                          onClick={() => {
                            action.setError(undefined);
                            setEditing(column);
                          }}
                        >
                          Edit deskripsi
                        </button>
                      </div>
                    </td>
                    <td>
                      <CertifyToggle
                        certified={column.description_certified}
                        disabled={action.busy}
                        onChange={(v) => patchColumn(column, { description_certified: v })}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      {editing && (
        <TextDialog
          title={`Deskripsi: ${editing.column_name}`}
          value={editing.description}
          certified={!!editing.description_certified}
          busy={action.busy}
          error={action.error}
          onSave={saveColumnDescription}
          onClose={() => setEditing(undefined)}
        >
          <div className="muted small">
            <span className="mono">{editing.column_name}</span> · {editing.data_type}
            {!!editing.sample_values?.length && <> · contoh: {editing.sample_values.slice(0, 5).join(", ")}</>}
          </div>
        </TextDialog>
      )}
    </>
  );
}
