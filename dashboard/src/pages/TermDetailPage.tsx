// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { Link, useParams } from "react-router-dom";
import { CertBadge, ErrorBanner, Loading } from "@/components/ui";
import { getTerm, updateTerm } from "@/features/terms/api";
import { ColumnAttributesSection } from "@/features/terms/components/ColumnAttributesSection";
import { SqlAttributesSection } from "@/features/terms/components/SqlAttributesSection";
import { TermOverviewCard } from "@/features/terms/components/TermOverviewCard";
import { useAction } from "@/hooks/useAction";
import { useFetch } from "@/hooks/useFetch";
import type { S } from "@/types";

export default function TermDetailPage() {
  const id = useParams().id!;
  const detail = useFetch(() => getTerm(id), [id]);
  const action = useAction();
  const term = detail.data?.data;

  async function patch(body: S["TermUpdate"]) {
    const saved = await action.run(() => updateTerm(id, body), "Tersimpan");
    if (saved && term) detail.setData({ data: { ...term, ...saved.data } });
  }

  // Certifying an attribute can roll the term's own state up or down.
  const setCertification = (certification: string | null) =>
    term && detail.setData({ data: { ...term, certification } });

  if (detail.error) return <ErrorBanner message={detail.error} />;
  if (!term) return <Loading />;

  return (
    <>
      <p>
        <Link to="/terms">← Semua business term</Link>
      </p>
      <div className="row spread page-head">
        <h1>{term.name}</h1>
        <CertBadge value={term.certification} />
      </div>
      <ErrorBanner message={action.error} />
      <TermOverviewCard term={term} busy={action.busy} onPatch={patch} />
      <ColumnAttributesSection termId={id} onCertification={setCertification} />
      <SqlAttributesSection termId={id} onCertification={setCertification} />
    </>
  );
}
