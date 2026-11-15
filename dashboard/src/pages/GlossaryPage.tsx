// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState } from "react";
import { PageHeader } from "@/components/layout";
import { Empty, ErrorBanner, Loading } from "@/components/ui";
import { glossaryQueries } from "@/features/glossary/api";
import { GlossaryForm } from "@/features/glossary/components/GlossaryForm";
import { GlossaryRow } from "@/features/glossary/components/GlossaryRow";
import { useFetch } from "@/hooks/useFetch";

export default function GlossaryPage() {
  const list = useFetch(glossaryQueries.entries());
  const [filter, setFilter] = useState("");

  const needle = filter.toLowerCase();
  const shown = (list.data ?? []).filter((a) => `${a.name} ${a.description}`.toLowerCase().includes(needle));

  return (
    <>
      <PageHeader title="Glossary">
        Singkatan dan istilah internal. Agent membacanya di setiap pertanyaan untuk memahami bahasa bisnis, misalnya
        “GMV” atau “nasabah aktif”.
      </PageHeader>
      <GlossaryForm onCreated={list.reload} />
      <ErrorBanner message={list.error} />
      {list.loading && !list.data && <Loading />}
      {list.data?.length === 0 && <Empty>Glossary masih kosong.</Empty>}
      {!!list.data?.length && (
        <div className="stack">
          <input
            type="search"
            className="narrow"
            placeholder="Saring…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            aria-label="Saring glossary"
          />
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th style={{ width: 220 }}>Istilah</th>
                  <th>Arti</th>
                  <th style={{ width: 160 }} />
                </tr>
              </thead>
              <tbody>
                {shown.map((a) => (
                  <GlossaryRow key={a.id} entry={a} onChange={list.reload} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}
