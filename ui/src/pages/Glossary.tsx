// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState } from "react";
import { api, useFetch, type S } from "../api";
import { Empty, ErrorBanner, Loading, PageHead, useAction } from "../ui";

type Acronym = S["Acronym"];

export default function Glossary() {
  const list = useFetch<Acronym[]>("/acronyms");
  const action = useAction();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [filter, setFilter] = useState("");

  async function add(e: React.FormEvent) {
    e.preventDefault();
    const created = await action.run(
      () => api<Acronym>("/acronyms", { method: "POST", json: { name, description } }),
      "Ditambahkan",
    );
    if (!created) return;
    setName("");
    setDescription("");
    list.reload();
  }

  const shown = (list.data ?? []).filter((a) =>
    `${a.name} ${a.description}`.toLowerCase().includes(filter.toLowerCase()),
  );

  return (
    <>
      <PageHead title="Glossary">
        Singkatan dan istilah internal. Agent membacanya di setiap pertanyaan untuk memahami bahasa bisnis,
        misalnya “GMV” atau “nasabah aktif”.
      </PageHead>
      <form className="card stack" onSubmit={add}>
        <h2 style={{ margin: 0 }}>Tambah istilah</h2>
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
      <ErrorBanner message={list.error} />
      {list.loading && !list.data && <Loading />}
      {list.data?.length === 0 && <Empty>Glossary masih kosong.</Empty>}
      {!!list.data?.length && (
        <>
          <input
            type="search"
            placeholder="Saring…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={{ maxWidth: 280, marginBottom: 8 }}
            aria-label="Saring glossary"
          />
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th style={{ width: 220 }}>Istilah</th>
                  <th>Arti</th>
                  <th style={{ width: 160 }} />
                </tr>
              </thead>
              <tbody>
                {shown.map((a) => (
                  <Row key={a.id} acronym={a} onChange={list.reload} />
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}

function Row({ acronym, onChange }: { acronym: Acronym; onChange: () => void }) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(acronym.name);
  const [description, setDescription] = useState(acronym.description);
  const action = useAction();

  async function save() {
    const saved = await action.run(
      () => api<Acronym>(`/acronyms/${acronym.id}`, { method: "PATCH", json: { name, description } }),
      "Tersimpan",
    );
    if (saved) {
      setEditing(false);
      onChange();
    }
  }

  async function remove() {
    if (!window.confirm(`Hapus “${acronym.name}” dari glossary?`)) return;
    const done = await action.run(() => api(`/acronyms/${acronym.id}`, { method: "DELETE" }), "Dihapus");
    if (done !== undefined) onChange();
  }

  if (editing) {
    return (
      <tr>
        <td>
          <input value={name} onChange={(e) => setName(e.target.value)} aria-label="Istilah" />
        </td>
        <td>
          <input value={description} onChange={(e) => setDescription(e.target.value)} aria-label="Arti" />
          <ErrorBanner message={action.error} />
        </td>
        <td>
          <div className="row">
            <button className="primary" onClick={save} disabled={action.busy || !name.trim()}>
              Simpan
            </button>
            <button onClick={() => setEditing(false)}>Batal</button>
          </div>
        </td>
      </tr>
    );
  }
  return (
    <tr>
      <td>
        <strong>{acronym.name}</strong>
      </td>
      <td>
        {acronym.description || <span className="muted">—</span>}
        <ErrorBanner message={action.error} />
      </td>
      <td>
        <div className="row">
          <button onClick={() => setEditing(true)}>Edit</button>
          <button className="danger" onClick={remove} disabled={action.busy}>
            Hapus
          </button>
        </div>
      </td>
    </tr>
  );
}
