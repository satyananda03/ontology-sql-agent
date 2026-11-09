// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState } from "react";
import { Empty, ErrorBanner, Loading } from "@/components/ui";
import { useFetch } from "@/hooks/useFetch";
import { replaceById } from "@/lib/utils";
import type { S } from "@/types";
import { listSqlAttributes } from "../api";
import { SqlAttributeCard } from "./SqlAttributeCard";
import { SqlAttributeForm } from "./SqlAttributeForm";

interface SqlAttributesSectionProps {
  termId: string;
  onCertification: (certification: string | null) => void;
}

export function SqlAttributesSection({ termId, onCertification }: SqlAttributesSectionProps) {
  const list = useFetch(() => listSqlAttributes(termId), [termId]);
  const [adding, setAdding] = useState(false);

  function replace(attr: S["SqlAttribute"], certification?: string | null) {
    if (list.data) list.setData({ ...list.data, data: replaceById(list.data.data, attr) });
    if (certification !== undefined) onCertification(certification);
  }

  return (
    <section className="card">
      <div className="row spread" style={{ marginBottom: 12 }}>
        <h2>Atribut SQL {list.data && <span className="muted">({list.data.total})</span>}</h2>
        {!adding && <button onClick={() => setAdding(true)}>+ Tambah atribut SQL</button>}
      </div>
      <p className="muted">Rumus atau filter bisnis dalam SQL, misalnya jumlah, rasio, atau syarat status. Agent memakainya sebagai definisi baku.</p>
      <ErrorBanner message={list.error} />
      {adding && (
        <SqlAttributeForm
          termId={termId}
          onDone={(created) => {
            setAdding(false);
            if (created) list.reload();
          }}
        />
      )}
      {list.loading && !list.data && <Loading />}
      {list.data?.data.length === 0 && !adding && <Empty>Belum ada atribut SQL.</Empty>}
      <div className="stack">
        {list.data?.data.map((attr) => (
          <SqlAttributeCard key={attr.id} termId={termId} attr={attr} onChange={replace} onDeleted={list.reload} />
        ))}
      </div>
    </section>
  );
}
