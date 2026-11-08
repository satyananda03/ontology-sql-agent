// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import type { S } from "@/types";

/** Where a search hit opens in this UI, if it has a page here. */
export function linkFor(hit: S["GlobalSearchItem"]): string | null {
  const crumb = (type: string) => hit.breadcrumbs?.find((b) => b.type === type)?.id;
  switch (hit.type) {
    case "Term":
      return `/terms/${hit.id}`;
    case "Table":
    case "View":
      return `/catalog?table=${hit.id}`;
    case "Column": {
      const table = crumb("Table") ?? crumb("View");
      return table ? `/catalog?table=${table}` : null;
    }
    case "CustomAnalysis":
      return `/analyses?id=${hit.id}`;
    default:
      // Attributes open on their Term.
      return hit.parent_id ? `/terms/${hit.parent_id}` : null;
  }
}
