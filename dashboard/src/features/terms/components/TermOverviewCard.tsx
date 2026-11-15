// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { Link } from "react-router-dom";
import { CertifyToggle, SynonymEditor, TextEditor } from "@/components/ui";
import type { S } from "@/types";

interface TermOverviewCardProps {
  term: S["TermDetail"];
  busy: boolean;
  onPatch: (body: S["TermUpdate"]) => Promise<unknown>;
  /** Saves a certify flag; rejects on failure. */
  onCertify: (body: S["TermUpdate"]) => Promise<unknown>;
}

/** Name, description, synonyms and tables of one term. */
export function TermOverviewCard({ term, busy, onPatch, onCertify }: TermOverviewCardProps) {
  return (
    <div className="card stack">
      <div className="row spread">
        <h3>Nama</h3>
        <CertifyToggle certified={term.name_certified} name="nama term" onChange={(v) => onCertify({ name_certified: v })} />
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
          name="deskripsi term"
          onChange={(v) => onCertify({ description_certified: v })}
        />
      </div>
      <TextEditor
        value={term.description}
        rows={4}
        busy={busy}
        certified={!!term.description_certified}
        onSave={(description, description_certified) => onPatch({ description, description_certified })}
      />
      <div className="stack tight">
        <h3>Sinonim</h3>
        <div className="muted small">
          Nama lain yang dipakai pengguna untuk term ini. Agent memakainya saat mencari tabel dan kolom.
        </div>
        <SynonymEditor value={term.synonyms ?? []} busy={busy} onChange={(synonyms) => onPatch({ synonyms })} />
      </div>
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
