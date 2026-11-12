// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState } from "react";

interface ComposerProps {
  pending: boolean;
  canClear: boolean;
  onAsk: (question: string) => void;
  onClear: () => void;
}

/** The question box: the tool's only argument. */
export function Composer({ pending, canClear, onAsk, onClear }: ComposerProps) {
  const [question, setQuestion] = useState("");

  function ask() {
    const q = question.trim();
    if (!q || pending) return;
    onAsk(q);
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
