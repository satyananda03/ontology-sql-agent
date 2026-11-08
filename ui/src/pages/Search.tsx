// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, type S } from "../api";
import { Badge, CertBadge, Empty, ErrorBanner, Loading, PageHead, useAction } from "../ui";

type Hit = S["GlobalSearchItem"];

/** Where a hit opens in this UI, if it has a page here. */
function linkFor(hit: Hit): string | null {
  const crumb = (type: string) => hit.breadcrumbs?.find((b) => b.type === type)?.id;
  switch (hit.type) {
    case "Term":
      return `/terms/${hit.id}`;
    case "Table":
    case "View":
      return `/catalog?table=${hit.id}`;
    case "Column":
      return crumb("Table") ?? crumb("View") ? `/catalog?table=${crumb("Table") ?? crumb("View")}` : null;
    case "CustomAnalysis":
      return `/analyses?id=${hit.id}`;
    default:
      // Attributes open on their Term.
      return hit.parent_id ? `/terms/${hit.parent_id}` : null;
  }
}

export default function Search() {
  const [params, setParams] = useSearchParams();
  const term = params.get("q") ?? "";
  const [draft, setDraft] = useState(term);
  const [inDescriptions, setInDescriptions] = useState(false);
  const [hits, setHits] = useState<Hit[]>();
  const action = useAction();

  useEffect(() => {
    if (term.trim().length < 2) return;
    action
      .run(() =>
        api<S["ListResponse_GlobalSearchItem_"]>("/search/global-search", {
          method: "POST",
          json: { search_term: term, filters: { description: inDescriptions, synonyms: true } },
        }),
      )
      .then((r) => r && setHits(r.data));
  }, [term, inDescriptions]);

  return (
    <>
      <PageHead title="Pencarian">Cari term, tabel, kolom, atribut, dan analisis di seluruh ontologi.</PageHead>
      <form
        className="row"
        style={{ marginBottom: 16 }}
        onSubmit={(e) => {
          e.preventDefault();
          setParams(draft ? { q: draft } : {});
        }}
      >
        <input
          type="search"
          placeholder="Minimal 2 karakter…"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          style={{ maxWidth: 420 }}
          aria-label="Kata kunci"
          autoFocus
        />
        <button className="primary" type="submit" disabled={draft.trim().length < 2}>
          Cari
        </button>
        <label className="check">
          <input type="checkbox" checked={inDescriptions} onChange={(e) => setInDescriptions(e.target.checked)} />
          Cari juga di deskripsi
        </label>
      </form>
      <ErrorBanner message={action.error} />
      {action.busy && <Loading label="Mencari…" />}
      {!action.busy && hits?.length === 0 && <Empty>Tidak ada hasil untuk “{term}”.</Empty>}
      {!action.busy && !!hits?.length && (
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
                return (
                  <tr key={`${hit.type}-${hit.id}`}>
                    <td>
                      {to ? <Link to={to}><strong>{hit.name}</strong></Link> : <strong>{hit.name}</strong>}
                      {hit.description && (
                        <div className="muted" style={{ fontSize: 12 }}>
                          {hit.description.slice(0, 140)}
                          {hit.description.length > 140 && "…"}
                        </div>
                      )}
                      {!!hit.synonyms?.length && (
                        <div className="muted" style={{ fontSize: 12 }}>
                          lewat sinonim: {hit.synonyms.join(", ")}
                        </div>
                      )}
                    </td>
                    <td>
                      <Badge>{hit.type}</Badge>
                    </td>
                    <td className="muted mono" style={{ fontSize: 12 }}>
                      {hit.breadcrumbs?.map((b) => b.name).join(" / ")}
                    </td>
                    <td>{hit.certified != null && <CertBadge value={hit.certified} />}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
