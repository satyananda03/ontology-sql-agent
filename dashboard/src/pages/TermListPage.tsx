// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/layout";
import { Empty, ErrorBanner, Loading, SearchForm } from "@/components/ui";
import { listTerms, TERMS_PAGE_SIZE } from "@/features/terms/api";
import { TermPagination } from "@/features/terms/components/TermPagination";
import { TermTable } from "@/features/terms/components/TermTable";
import { useFetch } from "@/hooks/useFetch";

export default function TermListPage() {
  const [params, setParams] = useSearchParams();
  const query = params.get("q") ?? "";
  const skip = Number(params.get("skip") ?? 0);
  const page = useFetch(() => listTerms(query, skip), [query, skip]);

  return (
    <>
      <PageHeader title="Terms">
        Konsep bisnis hasil kompilasi. Certify nama, deskripsi, dan atributnya agar agent memakai pengetahuan yang
        sudah diperiksa manusia.
      </PageHeader>
      <div className="toolbar">
        <SearchForm
          value={query}
          onSearch={(q) => setParams(q ? { q } : {})}
          placeholder="Cari nama term…"
          label="Cari nama term"
        >
          {page.data && <span className="muted">{page.data.total} term</span>}
        </SearchForm>
      </div>
      <ErrorBanner message={page.error} />
      {page.loading && !page.data && <Loading />}
      {page.data?.terms.length === 0 && <Empty>Tidak ada term{query && ` yang cocok dengan “${query}”`}.</Empty>}
      {!!page.data?.terms.length && <TermTable page={page.data} />}
      {page.data && (
        <TermPagination
          skip={skip}
          pageSize={TERMS_PAGE_SIZE}
          total={page.data.total}
          onSkip={(next) => setParams({ ...(query && { q: query }), skip: String(next) })}
        />
      )}
    </>
  );
}
