// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { describe, expect, it } from "vitest";
import { type Job, jobStatus } from "./jobs";

const job = (over: Partial<Job> = {}): Job => ({ kind: "compile", armed: true, failureBefore: "t0", ...over });

describe("jobStatus", () => {
  it("is running until the status was re-read after the trigger", () => {
    expect(jobStatus(job({ armed: false }), false, "t0")).toBe("running");
  });
  it("is running while the server says so", () => {
    expect(jobStatus(job(), true, "t0")).toBe("running");
  });
  it("is an error only on a failure newer than the run", () => {
    expect(jobStatus(job(), false, "t1")).toBe("error");
    expect(jobStatus(job(), false, "t0")).toBe("success");
    // A success clears last_failure_at: that is not a new failure.
    expect(jobStatus(job(), false, null)).toBe("success");
  });
  it("reports a failed ingest like a failed compilation", () => {
    expect(jobStatus(job({ kind: "ingest" }), false, "t1")).toBe("error");
  });
});
