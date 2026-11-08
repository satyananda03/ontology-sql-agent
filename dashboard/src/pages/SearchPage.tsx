// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/layout";
import { Empty, ErrorBanner, Loading, SearchForm } from "@/components/ui";
import { globalSearch, MIN_SEARCH_LENGTH } from "@/features/search/api";
import { SearchResults } from "@/features/search/components/SearchResults";
import { useAction } from "@/hooks/useAction";
import type { S } from "@/types";

export default function SearchPage() {
  const [params, setParams] = useSearchParams();
  const term = params.get("q") ?? "";
  const [inDescriptions, setInDescriptions] = useState(false);
  const [hits, setHits] = useState<S["GlobalSearchItem"][]>();
  const action = useAction();

  useEffect(() => {
    if (term.trim().length < MIN_SEARCH_LENGTH) return;
    action.run(() => globalSearch(term, inDescriptions)).then((result) => result && setHits(result));
    // Deliberately narrow deps: search again only when the inputs change.
  }, [term, inDescriptions]);

  return (
    <>
      <PageHeader title="Pencarian">Cari term, tabel, kolom, atribut, dan analisis di seluruh ontologi.</PageHeader>
      <div className="toolbar">
        <SearchForm
          value={term}
          onSearch={(q) => setParams(q ? { q } : {})}
          placeholder="Minimal 2 karakter…"
          label="Kata kunci"
          minLength={MIN_SEARCH_LENGTH}
          autoFocus
        >
          <label className="check">
            <input type="checkbox" checked={inDescriptions} onChange={(e) => setInDescriptions(e.target.checked)} />
            Cari juga di deskripsi
          </label>
        </SearchForm>
      </div>
      <ErrorBanner message={action.error} />
      {action.busy && <Loading label="Mencari…" />}
      {!action.busy && hits?.length === 0 && <Empty>Tidak ada hasil untuk “{term}”.</Empty>}
      {!action.busy && !!hits?.length && <SearchResults hits={hits} />}
    </>
  );
}
