// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState } from "react";
import { api, useFetch, type S } from "../api";
import { Badge, Empty, ErrorBanner, Loading, PageHead, useAction } from "../ui";

type Conn = Record<string, string>;

const FIELDS: [key: string, label: string, hint?: string][] = [
  ["host", "Host"],
  ["port", "Port", "Kosongkan untuk 5432."],
  ["database", "Database", "Juga menjadi nama koneksi; tidak bisa diubah setelah disimpan."],
  ["user", "User", "Gunakan role read-only."],
  ["password", "Password"],
  ["table_allow_regex", "Regex tabel yang diizinkan", "Opsional."],
  ["table_deny_regex", "Regex tabel yang dikecualikan", "Opsional; menang atas allow."],
];

export default function Connections() {
  const list = useFetch<S["ListResponse_PublicConnection_"]>("/connections");
  const fromEnv = useFetch<boolean>("/connections/source");
  const [editing, setEditing] = useState<Conn | "new" | null>(null);
  const action = useAction();

  async function remove(name: string) {
    if (!window.confirm(`Hapus koneksi “${name}”? Katalog dan ontologinya untuk database ini ikut di-reset.`)) return;
    const done = await action.run(
      () => api(`/connections/${encodeURIComponent(name)}`, { method: "DELETE" }),
      "Koneksi dihapus",
    );
    if (done !== undefined) list.reload();
  }

  return (
    <>
      <PageHead title="Koneksi">
        Database sumber (PostgreSQL). Menyimpan koneksi otomatis memicu ingest katalog. Skema yang di-ingest diatur
        di <code>ingest.yaml</code>.
      </PageHead>
      {fromEnv.data && (
        <div className="banner">
          <code>CONNECTION_STRINGS</code> terisi di .env. Ingest memakai variabel itu dan mengabaikan koneksi di
          halaman ini; kosongkan variabelnya untuk mengelola koneksi dari sini.
        </div>
      )}
      <ErrorBanner message={list.error ?? action.error} />
      {editing ? (
        <ConnectionForm
          initial={editing === "new" ? undefined : editing}
          onDone={(saved) => {
            setEditing(null);
            if (saved) list.reload();
          }}
        />
      ) : (
        <button className="primary" style={{ marginBottom: 16 }} onClick={() => setEditing("new")}>
          + Tambah koneksi
        </button>
      )}
      {list.loading && !list.data && <Loading />}
      {list.data?.data.length === 0 && <Empty>Belum ada koneksi tersimpan.</Empty>}
      {!!list.data?.data.length && (
        <table>
          <thead>
            <tr>
              <th>Database</th>
              <th>Host</th>
              <th>User</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {list.data.data.map(({ database_name, connection }) => {
              const conn = (connection ?? {}) as Conn;
              return (
                <tr key={database_name}>
                  <td>
                    <strong>{database_name}</strong> <Badge>{conn.type ?? "postgresql"}</Badge>
                  </td>
                  <td className="mono">
                    {conn.host}:{conn.port || 5432}
                  </td>
                  <td className="mono">{conn.user}</td>
                  <td>
                    <div className="row">
                      <button onClick={() => setEditing(conn)}>Edit</button>
                      <button className="danger" onClick={() => remove(database_name)} disabled={action.busy}>
                        Hapus
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </>
  );
}

function ConnectionForm({ initial, onDone }: { initial?: Conn; onDone: (saved?: boolean) => void }) {
  const [conn, setConn] = useState<Conn>({ type: "postgresql", ...initial, password: "" });
  const [tested, setTested] = useState(false);
  const action = useAction();
  const replacing = initial?.database;

  const set = (key: string, value: string) => {
    setConn((c) => ({ ...c, [key]: value }));
    setTested(false);
  };
  // Blank optional fields are left out rather than stored as "".
  const body = () => Object.fromEntries(Object.entries(conn).filter(([, v]) => v !== ""));

  async function test() {
    const ok = await action.run(
      () =>
        api<S["ConnectionTestResponse"]>("/connections/test", {
          method: "POST",
          json: { connection: body(), replacing: replacing ?? null },
        }),
      "Koneksi berhasil",
    );
    if (ok) setTested(true);
  }

  async function save() {
    const saved = await action.run(
      () =>
        replacing
          ? api(`/connections/${encodeURIComponent(replacing)}`, { method: "PUT", json: { connection: body() } })
          : api("/connections", { method: "POST", json: { connection: body() } }),
      "Tersimpan, ingest dimulai",
    );
    if (saved !== undefined) onDone(true);
  }

  return (
    <div className="card stack">
      <h2 style={{ margin: 0 }}>{replacing ? `Edit ${replacing}` : "Koneksi baru"}</h2>
      {FIELDS.map(([key, label, hint]) => (
        <label key={key} className="field">
          {label}
          {key === "password" && replacing && <span className="hint">Kosongkan untuk memakai password tersimpan.</span>}
          {hint && <span className="hint">{hint}</span>}
          <input
            type={key === "password" ? "password" : key === "port" ? "number" : "text"}
            value={conn[key] ?? ""}
            disabled={key === "database" && !!replacing}
            autoComplete={key === "password" ? "new-password" : "off"}
            onChange={(e) => set(key, e.target.value)}
          />
        </label>
      ))}
      <ErrorBanner message={action.error} />
      <div className="row">
        <button onClick={test} disabled={action.busy}>
          {action.busy ? <span className="spinner" /> : null} Tes koneksi
        </button>
        <button className="primary" onClick={save} disabled={action.busy || !tested} title={tested ? "" : "Tes koneksi dulu"}>
          Simpan
        </button>
        {tested && <Badge tone="solid">Tes berhasil</Badge>}
        <button onClick={() => onDone()} disabled={action.busy}>
          Batal
        </button>
      </div>
    </div>
  );
}
