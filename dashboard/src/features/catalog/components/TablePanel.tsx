// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { CertBadge, CertifyCheck, ErrorBanner, Loading, TextEditor } from "@/components/ui";
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

  async function patchNode<T extends { id: string }>(node: T, body: S["NodeUpdate"]): Promise<T | undefined> {
    const saved = await action.run(() => updateNode(node.id, body), "Tersimpan");
    return saved
      ? { ...node, description: saved.description, description_certified: saved.description_certified }
      : undefined;
  }

  async function patchTable(body: S["NodeUpdate"]) {
    const saved = await patchNode(table, body);
    if (saved) onChange(saved);
  }

  async function patchColumn(column: S["ColumnSummary"], body: S["NodeUpdate"]) {
    const saved = await patchNode(column, body);
    if (!saved || !columns.data) return;
    const data = columns.data.data;
    columns.setData({ ...columns.data, data: { ...data, columns: replaceById(data.columns ?? [], saved) } });
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
              onChange={(v) => patchTable({ description_certified: v })}
            />
          </div>
        </div>
        <TextEditor
          value={table.description}
          rows={3}
          busy={action.busy}
          placeholder="Belum ada deskripsi."
          onSave={(description) => patchTable({ description })}
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
                        <div className="muted small">contoh: {column.sample_values.slice(0, 5).join(", ")}</div>
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
                      <div className="stack tight">
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
