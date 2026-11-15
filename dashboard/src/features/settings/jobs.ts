// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { create } from "zustand";
import type { ProgressStatus } from "@/components/ui";

/** The long server jobs started from Settings. Regenerate runs as a compilation on the server. */
export type JobKind = "ingest" | "compile" | "regenerate";

export const JOBS: Record<JobKind, { title: string; running: string; success: string }> = {
  ingest: {
    title: "Sinkronkan Schema",
    running: "Membaca struktur database sumber ke katalog.",
    success: "Katalog sudah sinkron. Ada tabel baru? Lanjut ke Lengkapi term & atribut.",
  },
  compile: {
    title: "Lengkapi term & atribut",
    running: "Membuat term dan atribut untuk tabel baru. Bisa beberapa menit.",
    success: "Term dan atribut sudah dibuat.",
  },
  regenerate: {
    title: "Regenerate Ontology",
    running: "Membangun ulang ontologi dari nol. Bisa cukup lama.",
    success: "Ontologi sudah dibangun ulang.",
  },
};

export interface Job {
  kind: JobKind;
  /** False until the trigger returned and status was re-read: stale "not running" is no outcome yet. */
  armed: boolean;
  /** last_failure_at before the run, so a new failure stands out. */
  failureBefore?: string | null;
}

interface JobState {
  /** The run being followed, kept after it ends so its outcome stays readable. */
  job: Job | null;
  dialogOpen: boolean;
  setJob: (job: Job | null) => void;
  arm: () => void;
  setDialogOpen: (open: boolean) => void;
}

/** App-wide, so a run keeps reporting after the user leaves Settings. */
export const useJobStore = create<JobState>((set) => ({
  job: null,
  dialogOpen: false,
  setJob: (job) => set({ job }),
  arm: () => set((s) => ({ job: s.job && { ...s.job, armed: true } })),
  setDialogOpen: (dialogOpen) => set({ dialogOpen }),
}));

export function jobStatus(job: Job, running: boolean, failureNow?: string | null): ProgressStatus {
  if (!job.armed || running) return "running";
  if (failureNow && failureNow !== job.failureBefore) return "error";
  return "success";
}
