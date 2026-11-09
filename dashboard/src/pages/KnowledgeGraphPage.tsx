// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { PageHeader } from "@/components/layout";
import { Empty, ErrorBanner, Loading } from "@/components/ui";
import { getSourceDatabase } from "@/features/catalog/api";
import { KnowledgeGraphViewer } from "@/features/knowledge_graph/components/KnowledgeGraphViewer";
import { useFetch } from "@/hooks/useFetch";

export default function KnowledgeGraphPage() {
  const database = useFetch(getSourceDatabase);

  return (
    <>
      <PageHeader title="Knowledge Graph">
        Term dan tabel dalam satu graf. Klik node atau garis untuk melihat detailnya.
      </PageHeader>
      <ErrorBanner message={database.error} />
      {database.loading && !database.data && <Loading />}
      {database.data === null && (
        <Empty>Database sumber belum di-ingest. Jalankan Ingest ulang di Pengaturan → Operasi.</Empty>
      )}
      {database.data && (
        <div className="h-[calc(100vh-190px)] min-h-[480px] overflow-hidden rounded-3xl">
          <KnowledgeGraphViewer databaseId={database.data.id} />
        </div>
      )}
    </>
  );
}
