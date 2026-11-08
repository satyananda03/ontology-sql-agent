// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { Link, useNavigate } from "react-router-dom";
import { CertBadge } from "@/components/ui";
import { truncate } from "@/lib/utils";
import type { S } from "@/types";

const countFor = (entries: S["TermCountEntry"][] | undefined, termId: string): number =>
  entries?.find((e) => e.term_id === termId)?.count ?? 0;

export function TermTable({ page }: { page: S["TermsPageResponse"] }) {
  const navigate = useNavigate();
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Nama</th>
            <th>Deskripsi</th>
            <th>Atribut</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {page.terms.map((term) => (
            <tr key={term.id} className="clickable" onClick={() => navigate(`/terms/${term.id}`)}>
              <td>
                <Link to={`/terms/${term.id}`} onClick={(e) => e.stopPropagation()}>
                  <strong>{term.name}</strong>
                </Link>
                {!!term.synonyms?.length && <div className="muted small">{term.synonyms.join(", ")}</div>}
              </td>
              <td className="muted" style={{ maxWidth: 480 }}>
                {truncate(term.description, 160)}
              </td>
              <td className="muted">
                {countFor(page.column_attribute_counts, term.id)} kolom ·{" "}
                {countFor(page.sql_attribute_counts, term.id)} SQL
              </td>
              <td>
                <CertBadge value={term.certification} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
