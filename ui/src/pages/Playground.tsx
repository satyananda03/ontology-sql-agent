// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useRef, useState } from "react";
import { api, useFetch, type S } from "../api";
import { Badge, PageHead, toast } from "../ui";

type Result = S["SqlAgentResult"];
type Turn = { id: number; question: string; startedAt: number; seconds?: number; result?: Result; error?: string };

const STATUS: Record<Result["status"], [label: string, tone: "solid" | "outline" | "alert" | "alert-solid"]> = {
  ok: ["OK", "solid"],
  empty: ["Kosong", "outline"],
  unanswerable: ["Tak terjawab", "alert"],
  error: ["Error", "alert-solid"],
};

export default function Playground() {
  const dbs = useFetch<S["ListResponse_DatabaseSummary_"]>("/datasources/dbs");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState("");
  const [targetDb, setTargetDb] = useState("");
  const [evidence, setEvidence] = useState("");
  const bottom = useRef<HTMLDivElement>(null);
  const pending = turns.some((t) => !t.result && !t.error);

  // A block body on purpose: newer browsers return a Promise from
  // scrollIntoView, and an effect must return nothing or a cleanup function.
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns.length]);

  async function ask() {
    const q = question.trim();
    if (!q || pending) return;
    const id = Date.now();
    const update = (patch: Partial<Turn>) =>
      setTurns((all) => all.map((t) => (t.id === id ? { ...t, ...patch, seconds: (Date.now() - t.startedAt) / 1000 } : t)));
    setTurns((all) => [...all, { id, question: q, startedAt: id }]);
    setQuestion("");
    try {
      const result = await api<Result>("/sql-agent/query", {
        method: "POST",
        json: { question: q, target_db: targetDb || null, evidence },
      });
      update({ result });
    } catch (e) {
      update({ error: (e as Error).message });
    }
  }

  return (
    <>
      <PageHead title="Playground">
        Uji tool <em>search database records</em>. Setiap pesan dikirim apa adanya ke{" "}
        <code>POST /api/sql-agent/query</code> dan hasilnya sama persis dengan yang diterima agent lewat MCP. Pesan
        tidak saling terhubung dan riwayat hanya tersimpan di layar ini.
      </PageHead>
      <div className="chat" aria-live="polite">
        {turns.length === 0 && <p className="muted">Belum ada pertanyaan.</p>}
        {turns.map((turn) => (
          <TurnView key={turn.id} turn={turn} />
        ))}
        <div ref={bottom} />
      </div>
      <form
        className="composer stack"
        onSubmit={(e) => {
          e.preventDefault();
          ask();
        }}
      >
        <textarea
          rows={3}
          placeholder="Tulis pertanyaan… (Enter untuk kirim, Shift+Enter untuk baris baru)"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              ask();
            }
          }}
          aria-label="Pertanyaan"
          maxLength={4000}
        />
        <details>
          <summary className="muted" style={{ cursor: "pointer" }}>
            Opsi tool
          </summary>
          <div className="stack" style={{ marginTop: 8 }}>
            <label className="field">
              target_db
              <span className="hint">Kosongkan agar agent memilih sendiri.</span>
              <select value={targetDb} onChange={(e) => setTargetDb(e.target.value)}>
                <option value="">Otomatis</option>
                {dbs.data?.data.map((db) => (
                  <option key={db.id} value={db.name ?? ""}>
                    {db.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              evidence
              <span className="hint">Konteks tambahan yang biasanya dikirim agent pemanggil.</span>
              <textarea rows={2} value={evidence} onChange={(e) => setEvidence(e.target.value)} maxLength={8000} />
            </label>
          </div>
        </details>
        <div className="row">
          <button className="primary" disabled={pending || !question.trim()}>
            Kirim
          </button>
          {turns.length > 0 && (
            <button type="button" onClick={() => setTurns([])} disabled={pending}>
              Bersihkan
            </button>
          )}
        </div>
      </form>
    </>
  );
}

function TurnView({ turn }: { turn: Turn }) {
  const [now, setNow] = useState(Date.now());
  const done = turn.result || turn.error;
  useEffect(() => {
    if (done) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [done]);

  const r = turn.result;
  return (
    <>
      <div className="bubble-q">{turn.question}</div>
      <div className="card" style={{ marginBottom: 0 }}>
        {!done && (
          <div className="row muted" role="status">
            <span className="spinner" /> Agent bekerja… {Math.round((now - turn.startedAt) / 1000)} dtk
          </div>
        )}
        {turn.error && <div className="banner" style={{ margin: 0 }}>{turn.error}</div>}
        {r && (
          <div className="stack">
            <div className="row">
              <Badge tone={STATUS[r.status][1]}>{STATUS[r.status][0]}</Badge>
              <span className="muted">
                {r.row_count ?? 0} baris{r.truncated && " (terpotong)"} · {turn.seconds?.toFixed(1)} dtk
              </span>
            </div>
            <div className="answer">{r.text}</div>
            {r.sql && (
              <details>
                <summary style={{ cursor: "pointer" }}>SQL yang dijalankan</summary>
                <div className="stack" style={{ marginTop: 8, gap: 6 }}>
                  <pre className="code">{r.sql}</pre>
                  <div>
                    <button
                      type="button"
                      onClick={() => navigator.clipboard.writeText(r.sql!).then(() => toast("SQL disalin"))}
                    >
                      Salin SQL
                    </button>
                  </div>
                </div>
              </details>
            )}
          </div>
        )}
      </div>
    </>
  );
}
