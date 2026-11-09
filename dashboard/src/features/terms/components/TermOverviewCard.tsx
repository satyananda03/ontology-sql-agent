// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { Link } from "react-router-dom";
import { CertifyToggle, TextEditor } from "@/components/ui";
import type { S } from "@/types";

interface TermOverviewCardProps {
  term: S["TermDetail"];
  busy: boolean;
  onPatch: (body: S["TermUpdate"]) => void;
}

/** Name, description, synonyms and tables of one term. */
export function TermOverviewCard({ term, busy, onPatch }: TermOverviewCardProps) {
  return (
    <div className="card stack">
      <div className="row spread">
        <h3>Nama</h3>
        <CertifyToggle certified={term.name_certified} disabled={busy} onChange={(v) => onPatch({ name_certified: v })} />
      </div>
      <TextEditor
        value={term.name}
        rows={1}
        busy={busy}
        certified={!!term.name_certified}
        onSave={(name, name_certified) => onPatch({ name, name_certified })}
      />
      <div className="row spread">
        <h3>Deskripsi</h3>
        <CertifyToggle
          certified={term.description_certified}
          disabled={busy}
          onChange={(v) => onPatch({ description_certified: v })}
        />
      </div>
      <TextEditor
        value={term.description}
        rows={4}
        busy={busy}
        certified={!!term.description_certified}
        onSave={(description, description_certified) => onPatch({ description, description_certified })}
      />
      {!!term.synonyms?.length && (
        <div>
          <h3>Sinonim</h3>
          <div className="row">
            {term.synonyms.map((s) => (
              <span key={s} className="badge neutral">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}
      {!!term.tables?.length && (
        <div>
          <h3>Tabel</h3>
          <div className="row">
            {term.tables.map((table) => (
              <Link key={table.id} to={`/catalog?table=${table.id}`} className="badge neutral">
                {table.name}
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
