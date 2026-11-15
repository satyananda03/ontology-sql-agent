// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { Link, useParams } from "react-router-dom";
import { CertBadge, ErrorBanner, Loading } from "@/components/ui";
import { termQueries, updateTerm } from "@/features/terms/api";
import { ColumnAttributesSection } from "@/features/terms/components/ColumnAttributesSection";
import { SqlAttributesSection } from "@/features/terms/components/SqlAttributesSection";
import { TermOverviewCard } from "@/features/terms/components/TermOverviewCard";
import { useAction } from "@/hooks/useAction";
import { useFetch } from "@/hooks/useFetch";
import type { S } from "@/types";

export default function TermDetailPage() {
  const id = useParams().id!;
  const detail = useFetch(termQueries.detail(id));
  const action = useAction();
  const term = detail.data?.data;

  // Writes and updates what is shown, throwing on failure: certify calls it directly, edits through `patch`.
  async function save(body: S["TermUpdate"]) {
    const saved = await updateTerm(id, body);
    detail.setData((current) => ({ data: { ...current.data, ...saved.data } }));
    return saved;
  }

  const patch = (body: S["TermUpdate"]) => action.run(() => save(body), "Tersimpan");

  // Certifying an attribute can roll the term's own state up or down.
  const setCertification = (certification: string | null) =>
    detail.setData((current) => ({ data: { ...current.data, certification } }));

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
      <TermOverviewCard term={term} busy={action.busy} onPatch={patch} onCertify={save} />
      <ColumnAttributesSection termId={id} onCertification={setCertification} />
      <SqlAttributesSection termId={id} onCertification={setCertification} />
    </>
  );
}
