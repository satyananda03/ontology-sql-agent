// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState, type FormEvent } from "react";
import { ErrorBanner } from "@/components/ui";
import { useAction } from "@/hooks/useAction";
import { createAcronym } from "../api";

export function AcronymForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const action = useAction();

  async function submit(e: FormEvent) {
    e.preventDefault();
    const created = await action.run(() => createAcronym({ name, description }), "Ditambahkan");
    if (!created) return;
    setName("");
    setDescription("");
    onCreated();
  }

  return (
    <form className="card stack" onSubmit={submit}>
      <h2>Tambah istilah</h2>
      <div className="row" style={{ alignItems: "flex-start" }}>
        <label className="field" style={{ flex: "0 1 220px" }}>
          Istilah
          <input value={name} onChange={(e) => setName(e.target.value)} required maxLength={200} />
        </label>
        <label className="field" style={{ flex: "1 1 320px" }}>
          Arti
          <input value={description} onChange={(e) => setDescription(e.target.value)} maxLength={4000} />
        </label>
      </div>
      <ErrorBanner message={action.error} />
      <div>
        <button className="primary" disabled={action.busy || !name.trim()}>
          Tambah
        </button>
      </div>
    </form>
  );
}
