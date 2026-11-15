// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useFetch } from "@/hooks/useFetch";
import { settingsQueries } from "../api";
import { type JobKind, jobStatus, useJobStore } from "../jobs";

// Polled on every page so a run reports its outcome wherever the user is; faster while one runs.
// React Query pauses polling while the browser tab is hidden.
const POLL_MS = 10_000;
const POLL_RUNNING_MS = 2_000;
const poll = (q: { state: { data?: { running: boolean } } }) => (q.state.data?.running ? POLL_RUNNING_MS : POLL_MS);

/** Server job status, and how the followed job stands against it. */
export function useJobStatus() {
  const ingest = useFetch({ ...settingsQueries.ingestStatus(), refetchInterval: poll });
  const compile = useFetch({ ...settingsQueries.compilationStatus(), refetchInterval: poll });
  const job = useJobStore((s) => s.job);
  const ingesting = !!ingest.data?.running;
  const compiling = !!compile.data?.running;

  /** The job's last_failure_at; regenerate runs as a compilation, so it shares compile's. */
  const failureOf = (kind: JobKind) => (kind === "ingest" ? ingest : compile).data?.last_failure_at;

  const status = job && jobStatus(job, job.kind === "ingest" ? ingesting : compiling, failureOf(job.kind));
  // The job running now, if any. A run not started here cannot tell regenerate from compile.
  const active: JobKind | null =
    job && status === "running" ? job.kind : ingesting ? "ingest" : compiling ? "compile" : null;

  return { ingest, compile, job, status, active, failureOf };
}
