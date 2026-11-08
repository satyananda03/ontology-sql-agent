// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { Outlet } from "react-router-dom";
import { Sidebar } from "@/components/layout";
import { Toaster } from "@/components/ui";

/** Sidebar on the left, the current page on the right. */
export default function AppLayout() {
  return (
    <div className="shell">
      <Sidebar />
      <main className="content">
        <Outlet />
      </main>
      <Toaster />
    </div>
  );
}
