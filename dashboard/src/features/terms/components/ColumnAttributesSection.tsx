// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState } from "react";
import { CertifyToggle, Empty, ErrorBanner, Loading, TextDialog } from "@/components/ui";
import { useAction } from "@/hooks/useAction";
import { useFetch } from "@/hooks/useFetch";
import { replaceById } from "@/lib/utils";
import type { S } from "@/types";
import { listColumnAttributes, updateColumnAttribute } from "../api";

interface ColumnAttributesSectionProps {
  termId: string;
  onCertification: (certification: string | null) => void;
}

export function ColumnAttributesSection({ termId, onCertification }: ColumnAttributesSectionProps) {
  const list = useFetch(() => listColumnAttributes(termId), [termId]);
  const action = useAction();
  const [editing, setEditing] = useState<S["ColumnAttribute"]>();

  async function patch(attr: S["ColumnAttribute"], body: S["ColumnAttributeUpdate"]) {
    const saved = await action.run(() => updateColumnAttribute(termId, attr.id, body), "Tersimpan");
    if (!saved || !list.data) return false;
    list.setData({ ...list.data, data: replaceById(list.data.data, saved.data) });
    onCertification(saved.term_certification);
    return true;
  }

  async function saveDescription(description: string, certified?: boolean) {
    if (editing && (await patch(editing, { description, certified }))) setEditing(undefined);
  }

  return (
    <section className="card">
      <h2>Atribut kolom {list.data && <span className="muted">({list.data.total})</span>}</h2>
      <ErrorBanner message={list.error ?? (editing ? undefined : action.error)} />
      {list.loading && !list.data && <Loading />}
      {list.data?.data.length === 0 && <Empty>Term ini belum punya atribut kolom.</Empty>}
      {!!list.data?.data.length && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Atribut</th>
                <th>Kolom sumber</th>
                <th style={{ width: "45%" }}>Deskripsi</th>
                <th>Review</th>
              </tr>
            </thead>
            <tbody>
              {list.data.data.map((attr) => (
                <tr key={attr.id}>
                  <td>
                    <strong>{attr.name}</strong>
                    <div className="muted mono">{attr.datatype}</div>
                  </td>
                  <td className="mono">
                    {attr.source_column}
                    {!!attr.sample_values?.length && (
                      <div className="muted small">contoh: {attr.sample_values.slice(0, 5).join(", ")}</div>
                    )}
                  </td>
                  <td>
                    <div className="stack tight">
                      <div className={attr.description ? "clamp" : "muted"}>
                        {attr.description || "Belum ada deskripsi."}
                      </div>
                      <button
                        className="link small"
                        onClick={() => {
                          action.setError(undefined);
                          setEditing(attr);
                        }}
                      >
                        Edit deskripsi
                      </button>
                    </div>
                  </td>
                  <td>
                    <CertifyToggle
                      certified={attr.certified}
                      disabled={action.busy}
                      onChange={(certified) => patch(attr, { certified })}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {editing && (
        <TextDialog
          title={`Deskripsi: ${editing.name}`}
          value={editing.description}
          certified={!!editing.certified}
          busy={action.busy}
          error={action.error}
          onSave={saveDescription}
          onClose={() => setEditing(undefined)}
        >
          <div className="muted small">
            Kolom sumber <span className="mono">{editing.source_column}</span> · {editing.datatype}
            {!!editing.sample_values?.length && <> · contoh: {editing.sample_values.slice(0, 5).join(", ")}</>}
          </div>
        </TextDialog>
      )}
    </section>
  );
}
