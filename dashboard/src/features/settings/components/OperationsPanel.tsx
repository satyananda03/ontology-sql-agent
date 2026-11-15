// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import type { ReactNode } from "react";
import { ErrorBanner, Spinner } from "@/components/ui";
import { useAction } from "@/hooks/useAction";
import { formatDateTime } from "@/lib/utils";
import { regenerateOntology, triggerCompilation, triggerIngest } from "../api";
import { useJobStatus } from "../hooks/useJobStatus";
import { JOBS, type JobKind, useJobStore } from "../jobs";

const REGENERATE_WARNING =
  "Regenerate ontologi?\n\nSeluruh ontologi dihapus lalu dikompilasi ulang dari nol: term, atribut, hasil review, dan few-shot examples. Few-shot examples TIDAK dibuat ulang. Deskripsi katalog tetap.\n\nExport model dulu bila perlu cadangan.";

/** The three jobs that keep the catalog and ontology current. Progress and outcome show in JobMonitor. */
export function OperationsPanel() {
  const { ingest, compile, active, failureOf } = useJobStatus();
  const setJob = useJobStore((s) => s.setJob);
  const arm = useJobStore((s) => s.arm);
  const setDialogOpen = useJobStore((s) => s.setDialogOpen);
  const action = useAction();
  // One job at a time: the ingestion service queues a second one anyway.
  const busy = action.busy || active !== null;

  async function start(kind: JobKind, trigger: () => Promise<unknown>) {
    setJob({ kind, armed: false, failureBefore: failureOf(kind) });
    setDialogOpen(true);
    if ((await action.run(trigger)) === undefined) {
      // The trigger itself failed: the banner says why, nothing is running.
      setDialogOpen(false);
      setJob(null);
      return;
    }
    await (kind === "ingest" ? ingest : compile).reload();
    arm();
  }

  function runRegenerate() {
    if (window.confirm(REGENERATE_WARNING)) void start("regenerate", regenerateOntology);
  }

  /** A job's button; while that job runs it turns into a spinner that reopens the progress dialog. */
  function jobButton(kind: JobKind, className: string, run: () => void) {
    if (active === kind)
      return (
        <button className={className} onClick={() => setDialogOpen(true)} aria-busy="true">
          <Spinner /> Lihat progres
        </button>
      );
    return (
      <button className={className} onClick={run} disabled={busy}>
        {JOBS[kind].title}
      </button>
    );
  }

  const c = compile.data;
  return (
    <section className="card stack">
      <h2>Operasi</h2>
      <ErrorBanner message={ingest.error ?? compile.error ?? action.error} />
      <Operation title={JOBS.ingest.title} action={jobButton("ingest", "primary", () => start("ingest", triggerIngest))}>
        Sinkronkan struktur database sumber (tabel, kolom, key) ke katalog. Jalankan setelah ada tabel atau kolom
        baru.
      </Operation>
      <Operation
        title={JOBS.compile.title}
        action={jobButton("compile", "primary", () => start("compile", triggerCompilation))}
      >
        Buat term dan atribut untuk tabel yang belum punya, setelah selesai sinkronisasi skema.
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
      <Operation title={JOBS.regenerate.title} action={jobButton("regenerate", "danger", runRegenerate)}>
        Hapus seluruh ontologi lalu kompilasi ulang dari nol. Hasil review dan few-shot examples ikut hilang.
      </Operation>
    </section>
  );
}

interface OperationProps {
  title: string;
  action: ReactNode;
  children: ReactNode;
}

function Operation({ title, action, children }: OperationProps) {
  return (
    <div className="operation">
      <div className="operation-body">
        <h3>{title}</h3>
        <div className="muted">{children}</div>
      </div>
      {action}
    </div>
  );
}
