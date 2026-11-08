// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

interface TermPaginationProps {
  skip: number;
  pageSize: number;
  total: number;
  onSkip: (skip: number) => void;
}

export function TermPagination({ skip, pageSize, total, onSkip }: TermPaginationProps) {
  if (total <= pageSize) return null;
  return (
    <div className="row" style={{ marginTop: 16 }}>
      <button disabled={skip === 0} onClick={() => onSkip(Math.max(0, skip - pageSize))}>
        ← Sebelumnya
      </button>
      <span className="muted">
        {skip + 1}–{Math.min(skip + pageSize, total)} dari {total}
      </span>
      <button disabled={skip + pageSize >= total} onClick={() => onSkip(skip + pageSize)}>
        Berikutnya →
      </button>
    </div>
  );
}
