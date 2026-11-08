// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useRef, useState } from "react";
import { PageHeader } from "@/components/layout";
import { querySqlAgent } from "@/features/playground/api";
import { Composer } from "@/features/playground/components/Composer";
import { TurnView } from "@/features/playground/components/TurnView";
import type { Turn } from "@/features/playground/types";

export default function PlaygroundPage() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const bottom = useRef<HTMLDivElement>(null);
  const pending = turns.some((t) => !t.result && !t.error);

  // A block body on purpose: newer browsers return a Promise from
  // scrollIntoView, and an effect must return nothing or a cleanup function.
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns.length]);

  async function ask(question: string, evidence: string) {
    const id = Date.now();
    const finish = (patch: Partial<Turn>) =>
      setTurns((all) =>
        all.map((t) => (t.id === id ? { ...t, ...patch, seconds: (Date.now() - t.startedAt) / 1000 } : t)),
      );
    setTurns((all) => [...all, { id, question, startedAt: id }]);
    try {
      finish({ result: await querySqlAgent(question, evidence) });
    } catch (e) {
      finish({ error: (e as Error).message });
    }
  }

  return (
    <>
      <PageHeader title="Playground">
        Uji tool <em>search database records</em>. Setiap pesan dikirim apa adanya ke{" "}
        <code>POST /api/sql-agent/query</code> dan hasilnya sama persis dengan yang diterima agent lewat MCP. Pesan
        tidak saling terhubung dan riwayat hanya tersimpan di layar ini.
      </PageHeader>
      <div className="chat" aria-live="polite">
        {turns.length === 0 && <p className="muted">Belum ada pertanyaan.</p>}
        {turns.map((turn) => (
          <TurnView key={turn.id} turn={turn} />
        ))}
        <div ref={bottom} />
      </div>
      <Composer pending={pending} canClear={turns.length > 0} onAsk={ask} onClear={() => setTurns([])} />
    </>
  );
}
