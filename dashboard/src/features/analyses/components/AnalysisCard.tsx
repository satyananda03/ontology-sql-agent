// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState } from "react";
import { ErrorBanner } from "@/components/ui";
import { useAction } from "@/hooks/useAction";
import type { S } from "@/types";
import { deleteAnalysis } from "../api";
import { AnalysisForm } from "./AnalysisForm";

interface AnalysisCardProps {
  analysis: S["CustomAnalysis"];
  highlighted: boolean;
  onChange: () => void;
}

export function AnalysisCard({ analysis, highlighted, onChange }: AnalysisCardProps) {
  const [editing, setEditing] = useState(false);
  const action = useAction();

  async function remove() {
    if (!window.confirm(`Hapus analisis “${analysis.name}”?`)) return;
    const done = await action.run(() => deleteAnalysis(analysis.id), "Dihapus");
    if (done !== undefined) onChange();
  }

  if (editing) {
    return (
      <AnalysisForm
        analysis={analysis}
        onDone={(saved) => {
          setEditing(false);
          if (saved) onChange();
        }}
      />
    );
  }

  return (
    <div className={`card stack ${highlighted ? "highlighted" : ""}`}>
      <div className="row spread">
        <strong>{analysis.name}</strong>
        <div className="row">
          <button onClick={() => setEditing(true)}>Edit</button>
          <button className="danger" onClick={remove} disabled={action.busy}>
            Hapus
          </button>
        </div>
      </div>
      <ErrorBanner message={action.error} />
      {analysis.description && <p>{analysis.description}</p>}
      <pre className="code">{analysis.sql}</pre>
    </div>
  );
}
