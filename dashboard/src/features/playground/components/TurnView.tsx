// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useState } from "react";
import { Badge, Spinner, toast, type BadgeTone } from "@/components/ui";
import type { S } from "@/types";
import type { Turn } from "../types";

const STATUS: Record<S["SqlAgentResult"]["status"], [label: string, tone: BadgeTone]> = {
  ok: ["OK", "success"],
  empty: ["Kosong", "neutral"],
  unanswerable: ["Tak terjawab", "warning"],
  error: ["Error", "error"],
};

/** Ticks once a second while *running*, so the elapsed time stays live. */
function useNow(running: boolean): number {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [running]);
  return now;
}

export function TurnView({ turn }: { turn: Turn }) {
  const done = !!(turn.result || turn.error);
  const now = useNow(!done);
  const r = turn.result;

  return (
    <>
      <div className="bubble-q">{turn.question}</div>
      <div className="card">
        {!done && (
          <div className="row muted" role="status">
            <Spinner /> Agent bekerja… {Math.round((now - turn.startedAt) / 1000)} dtk
          </div>
        )}
        {turn.error && (
          <div className="banner" style={{ margin: 0 }}>
            {turn.error}
          </div>
        )}
        {r && (
          <div className="stack">
            <div className="row">
              <Badge tone={STATUS[r.status][1]}>{STATUS[r.status][0]}</Badge>
              <span className="muted">
                {r.row_count ?? 0} baris{r.truncated && " (terpotong)"} · {turn.seconds?.toFixed(1)} dtk
              </span>
            </div>
            <div className="answer">{r.text}</div>
            {r.sql && <SqlDetails sql={r.sql} />}
          </div>
        )}
      </div>
    </>
  );
}

function SqlDetails({ sql }: { sql: string }) {
  return (
    <details>
      <summary>SQL yang dijalankan</summary>
      <div className="stack tight" style={{ marginTop: 8 }}>
        <pre className="code">{sql}</pre>
        <div>
          <button type="button" onClick={() => navigator.clipboard.writeText(sql).then(() => toast("SQL disalin"))}>
            Salin SQL
          </button>
        </div>
      </div>
    </details>
  );
}
