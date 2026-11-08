// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/layout";
import { Empty, ErrorBanner, Loading, SearchForm } from "@/components/ui";
import { listAnalyses } from "@/features/analyses/api";
import { AnalysisCard } from "@/features/analyses/components/AnalysisCard";
import { AnalysisForm } from "@/features/analyses/components/AnalysisForm";
import { useFetch } from "@/hooks/useFetch";

export default function AnalysesPage() {
  const [params, setParams] = useSearchParams();
  const query = params.get("q") ?? "";
  const focus = params.get("id");
  const [adding, setAdding] = useState(false);
  const list = useFetch(() => listAnalyses(query), [query]);

  return (
    <>
      <PageHeader title="Custom analyses">
        Contoh pertanyaan beserta SQL yang sudah diverifikasi. Agent mengambil yang relevan sebagai referensi saat
        menyusun query, jadi contoh yang baik langsung menaikkan akurasi.
      </PageHeader>
      <div className="row spread toolbar">
        <SearchForm
          value={query}
          onSearch={(q) => setParams(q ? { q } : {})}
          placeholder="Cari analisis…"
          label="Cari analisis"
        />
        {!adding && (
          <button className="primary" onClick={() => setAdding(true)}>
            + Tambah analisis
          </button>
        )}
      </div>
      {adding && (
        <AnalysisForm
          onDone={(saved) => {
            setAdding(false);
            if (saved) list.reload();
          }}
        />
      )}
      <ErrorBanner message={list.error} />
      {list.loading && !list.data && <Loading />}
      {list.data?.data.length === 0 && !adding && <Empty>Belum ada custom analysis.</Empty>}
      {list.data?.data.map((analysis) => (
        <AnalysisCard key={analysis.id} analysis={analysis} highlighted={analysis.id === focus} onChange={list.reload} />
      ))}
    </>
  );
}
