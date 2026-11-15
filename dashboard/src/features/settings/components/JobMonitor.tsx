// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useRef } from "react";
import { ProgressDialog, type ProgressStatus, toast } from "@/components/ui";
import { useJobStatus } from "../hooks/useJobStatus";
import { JOBS, type JobKind, useJobStore } from "../jobs";

/**
 * Mounted once in the app layout: follows the running job on every page, shows
 * its progress dialog, and toasts the outcome when the dialog is closed.
 */
export function JobMonitor() {
  const { job, status, active, failureOf } = useJobStatus();
  const dialogOpen = useJobStore((s) => s.dialogOpen);
  const setJob = useJobStore((s) => s.setJob);
  const setDialogOpen = useJobStore((s) => s.setDialogOpen);
  const lastFailure = active ? failureOf(active) : null;

  // Follow a run started elsewhere (before this page loaded, or by someone else).
  useEffect(() => {
    if (active && status !== "running") setJob({ kind: active, armed: true, failureBefore: lastFailure });
  }, [active, status, lastFailure, setJob]);

  // The open dialog already shows the outcome; otherwise a toast reports it.
  const lastStatus = useRef<ProgressStatus | null>(null);
  useEffect(() => {
    if (!job || !status) return;
    if (lastStatus.current === "running" && status !== "running" && !dialogOpen)
      toast(outcomeToast(job.kind, status), status === "success" ? "success" : "error");
    lastStatus.current = status;
  }, [job, status, dialogOpen]);

  if (!job || !status) return null;
  return (
    <ProgressDialog open={dialogOpen} title={JOBS[job.kind].title} status={status} onClose={() => setDialogOpen(false)}>
      {progressMessage(job.kind, status)}
    </ProgressDialog>
  );
}

function progressMessage(kind: JobKind, status: ProgressStatus): string {
  if (status === "success") return JOBS[kind].success;
  if (status === "error") return "Proses gagal. Detailnya ada di log ingestion service.";
  return JOBS[kind].running;
}

function outcomeToast(kind: JobKind, status: ProgressStatus): string {
  return `${JOBS[kind].title} ${status === "success" ? "selesai" : "gagal"}`;
}
