// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import type { ButtonHTMLAttributes } from "react";
import { Spinner } from "./Feedback";

interface BusyButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** The button's action is running: show a spinner and block another click. */
  busy?: boolean;
}

/** A button that shows a spinner and stays disabled while its action runs. */
export function BusyButton({ busy = false, disabled, children, ...props }: BusyButtonProps) {
  return (
    <button {...props} disabled={busy || disabled} aria-busy={busy}>
      {busy && <Spinner />}
      {children}
    </button>
  );
}
