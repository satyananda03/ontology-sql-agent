// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { CertBadge, CertifyCheck, Empty, ErrorBanner, Loading, TextEditor } from "@/components/ui";
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

  async function patch(attr: S["ColumnAttribute"], body: S["ColumnAttributeUpdate"]) {
    const saved = await action.run(() => updateColumnAttribute(termId, attr.id, body), "Tersimpan");
    if (!saved || !list.data) return;
    list.setData({ ...list.data, data: replaceById(list.data.data, saved.data) });
    onCertification(saved.term_certification);
  }

  return (
    <section className="card">
      <h2>Atribut kolom {list.data && <span className="muted">({list.data.total})</span>}</h2>
      <ErrorBanner message={list.error ?? action.error} />
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
                    <TextEditor
                      value={attr.description}
                      rows={2}
                      busy={action.busy}
                      onSave={(description) => patch(attr, { description })}
                    />
                  </td>
                  <td>
                    <div className="stack tight">
                      <CertBadge value={attr.certified} />
                      <CertifyCheck
                        label="Certify"
                        checked={attr.certified}
                        disabled={action.busy}
                        onChange={(certified) => patch(attr, { certified })}
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
  );
}
