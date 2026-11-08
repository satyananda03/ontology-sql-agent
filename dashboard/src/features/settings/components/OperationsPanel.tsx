// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import type { ReactNode } from "react";
import { Badge, ErrorBanner } from "@/components/ui";
import { useAction } from "@/hooks/useAction";
import { formatDateTime } from "@/lib/utils";
import { getCompilationStatus, getIngestStatus, regenerateOntology, triggerCompilation, triggerIngest } from "../api";
import { usePolledFetch } from "../hooks/usePolledFetch";

const REGENERATE_WARNING =
  "Regenerate ontologi?\n\nSeluruh ontologi dihapus lalu dikompilasi ulang dari nol: term, atribut, hasil review, dan custom analyses. Custom analyses TIDAK dibuat ulang. Deskripsi katalog tetap.\n\nExport model dulu bila perlu cadangan.";

/** The three jobs that keep the catalog and ontology current. Nothing runs on its own. */
export function OperationsPanel() {
  const ingest = usePolledFetch(getIngestStatus);
  const compile = usePolledFetch(getCompilationStatus);
  const action = useAction();
  const ingesting = !!ingest.data?.running;
  const compiling = !!compile.data?.running;
  // One job at a time: the ingestion service queues a second one anyway.
  const busy = action.busy || ingesting || compiling;

  async function runIngest() {
    const status = await action.run(triggerIngest, "Ingest dimulai");
    if (status) ingest.setData(status);
  }

  async function runCompile() {
    await action.run(triggerCompilation, "Kompilasi dimulai");
    compile.reload();
  }

  async function runRegenerate() {
    if (!window.confirm(REGENERATE_WARNING)) return;
    await action.run(regenerateOntology, "Regenerate dimulai");
    compile.reload();
  }

  const c = compile.data;
  return (
    <section className="card stack">
      <h2>Operasi</h2>
      <p className="muted">Tidak ada yang berjalan otomatis. Satu operasi berjalan pada satu waktu.</p>
      <ErrorBanner message={ingest.error ?? compile.error ?? action.error} />
      <Operation
        title="Ingest ulang"
        running={ingesting}
        action={
          <button className="primary" onClick={runIngest} disabled={busy}>
            Ingest ulang
          </button>
        }
      >
        Sinkronkan struktur database sumber (tabel, kolom, key) ke katalog. Jalankan setelah ada tabel atau kolom
        baru. Baris baru tidak perlu: agent membaca data langsung dari sumber.
      </Operation>
      <Operation
        title="Kompilasi"
        running={compiling}
        action={
          <button className="primary" onClick={runCompile} disabled={busy}>
            Jalankan kompilasi
          </button>
        }
      >
        Buat term dan atribut untuk tabel yang belum punya, biasanya setelah ingest ulang. Tabel yang sudah
        dikompilasi tidak disentuh.
        {c && (
          <dl className="row facts" style={{ marginTop: 8 }}>
            <div>
              <dt>Terakhir berhasil</dt>
              <dd>{formatDateTime(c.last_success_at)}</dd>
            </div>
            <div>
              <dt>Terakhir gagal</dt>
              <dd className={c.last_failure_at ? "text-error" : undefined}>{formatDateTime(c.last_failure_at)}</dd>
            </div>
          </dl>
        )}
      </Operation>
      <Operation
        title="Regenerate ontologi"
        action={
          <button className="danger" onClick={runRegenerate} disabled={busy}>
            Regenerate ontologi
          </button>
        }
      >
        Hapus seluruh ontologi lalu kompilasi ulang dari nol. Hasil review dan custom analyses ikut hilang.
      </Operation>
    </section>
  );
}

interface OperationProps {
  title: string;
  running?: boolean;
  action: ReactNode;
  children: ReactNode;
}

function Operation({ title, running, action, children }: OperationProps) {
  return (
    <div className="operation">
      <div className="operation-body">
        <div className="row">
          <h3>{title}</h3>
          {running && <Badge tone="info">Berjalan</Badge>}
        </div>
        <div className="muted">{children}</div>
      </div>
      {action}
    </div>
  );
}
