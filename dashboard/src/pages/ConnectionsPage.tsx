// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { PageHeader } from "@/components/layout";
import { ErrorBanner, Loading } from "@/components/ui";
import { getConnection } from "@/features/connections/api";
import { useFetch } from "@/hooks/useFetch";

export default function ConnectionsPage() {
  const connection = useFetch(getConnection);
  const c = connection.data;

  return (
    <>
      <PageHeader title="Koneksi">
        Satu database sumber (PostgreSQL), diatur lewat <code>CONNECTION_STRINGS</code> di <code>.env</code>. Untuk
        menggantinya, ubah variabel itu lalu restart backend dan ingestion service. Skema yang di-ingest diatur di{" "}
        <code>ingest.yaml</code>.
      </PageHeader>
      <ErrorBanner message={connection.error} />
      {connection.loading && !c && <Loading />}
      {c && (
        <section className="card">
          <dl className="row facts">
            <div>
              <dt className="muted">Database</dt>
              <dd className="mono">{c.database}</dd>
            </div>
            <div>
              <dt className="muted">Host</dt>
              <dd className="mono">
                {c.host}:{c.port}
              </dd>
            </div>
            <div>
              <dt className="muted">User</dt>
              <dd className="mono">{c.user}</dd>
            </div>
          </dl>
        </section>
      )}
    </>
  );
}
