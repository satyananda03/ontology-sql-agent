// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState } from "react";
import { toast } from "@/components/ui";

/**
 * Run one async action at a time: tracks `busy`, keeps the last error for a
 * banner, and toasts *done* on success. Returns the action's result, or
 * undefined when it failed.
 */
export function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();

  async function run<T>(action: () => Promise<T>, done?: string): Promise<T | undefined> {
    setBusy(true);
    setError(undefined);
    try {
      const result = await action();
      if (done) toast(done);
      return result;
    } catch (e) {
      setError((e as Error).message);
      return undefined;
    } finally {
      setBusy(false);
    }
  }

  return { busy, error, setError, run };
}
