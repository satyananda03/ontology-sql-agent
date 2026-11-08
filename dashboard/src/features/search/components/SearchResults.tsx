// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { Link } from "react-router-dom";
import { Badge, CertBadge } from "@/components/ui";
import { truncate } from "@/lib/utils";
import type { S } from "@/types";
import { linkFor } from "../links";

export function SearchResults({ hits }: { hits: S["GlobalSearchItem"][] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Nama</th>
            <th>Jenis</th>
            <th>Lokasi</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {hits.map((hit) => {
            const to = linkFor(hit);
            const name = <strong>{hit.name}</strong>;
            return (
              <tr key={`${hit.type}-${hit.id}`}>
                <td>
                  {to ? <Link to={to}>{name}</Link> : name}
                  {hit.description && <div className="muted small">{truncate(hit.description, 140)}</div>}
                  {!!hit.synonyms?.length && (
                    <div className="muted small">lewat sinonim: {hit.synonyms.join(", ")}</div>
                  )}
                </td>
                <td>
                  <Badge>{hit.type}</Badge>
                </td>
                <td className="muted mono small">{hit.breadcrumbs?.map((b) => b.name).join(" / ")}</td>
                <td>{hit.certified != null && <CertBadge value={hit.certified} />}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
