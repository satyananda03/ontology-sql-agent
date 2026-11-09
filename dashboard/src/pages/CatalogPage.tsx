// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/layout";
import { Empty, ErrorBanner, Loading } from "@/components/ui";
import { CatalogTree } from "@/features/catalog/components/CatalogTree";
import { TablePanel } from "@/features/catalog/components/TablePanel";
import { useCatalogTree } from "@/features/catalog/hooks/useCatalogTree";

export default function CatalogPage() {
  const [params, setParams] = useSearchParams();
  const tableId = params.get("table");
  const tree = useCatalogTree(tableId);

  return (
    <>
      <PageHeader title="Katalog">
        Database, skema, tabel, dan kolom yang di-ingest. Deskripsinya dikirim ke agent saat menyusun SQL. Certify
        menandai yang sudah diperiksa manusia.
      </PageHeader>
      <ErrorBanner message={tree.error} />
      <div className="grid2">
        <CatalogTree tree={tree} selectedId={tableId} onSelect={(table) => setParams({ table })} />
        <div>
          {tree.selected ? (
            <TablePanel key={tree.selected.id} table={tree.selected} onChange={tree.updateTable} />
          ) : tableId ? (
            <Loading />
          ) : (
            <Empty>Pilih tabel di sebelah kiri untuk me-review deskripsinya.</Empty>
          )}
        </div>
      </div>
    </>
  );
}
