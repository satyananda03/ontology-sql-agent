// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState } from "react";

interface ComposerProps {
  pending: boolean;
  canClear: boolean;
  onAsk: (question: string, evidence: string) => void;
  onClear: () => void;
}

/** The question box plus the tool's optional evidence. */
export function Composer({ pending, canClear, onAsk, onClear }: ComposerProps) {
  const [question, setQuestion] = useState("");
  const [evidence, setEvidence] = useState("");

  function ask() {
    const q = question.trim();
    if (!q || pending) return;
    onAsk(q, evidence);
    setQuestion("");
  }

  return (
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
        <summary className="muted">Opsi tool</summary>
        <div className="stack" style={{ marginTop: 8 }}>
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
        {canClear && (
          <button type="button" onClick={onClear} disabled={pending}>
            Bersihkan
          </button>
        )}
      </div>
    </form>
  );
}
