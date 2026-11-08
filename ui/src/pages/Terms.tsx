// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, useFetch, type S } from "../api";
import {
  CertBadge,
  CertifyCheck,
  Empty,
  ErrorBanner,
  Loading,
  PageHead,
  TextEditor,
  useAction,
} from "../ui";

const PAGE = 50;

export function TermList() {
  const [params, setParams] = useSearchParams();
  const query = params.get("q") ?? "";
  const skip = Number(params.get("skip") ?? 0);
  const [draft, setDraft] = useState(query);
  const navigate = useNavigate();

  const qs = new URLSearchParams({ skip: String(skip), limit: String(PAGE) });
  if (query) qs.set("query", query);
  const { data, error, loading } = useFetch<S["TermsPageResponse"]>(`/terms?${qs}`);

  const count = (entries: S["TermCountEntry"][] | undefined, id: string) =>
    entries?.find((e) => e.term_id === id)?.count ?? 0;

  return (
    <>
      <PageHead title="Terms">
        Konsep bisnis hasil kompilasi. Certify nama, deskripsi, dan atributnya agar agent memakai
        pengetahuan yang sudah diperiksa manusia.
      </PageHead>
      <form
        className="row"
        style={{ marginBottom: 16 }}
        onSubmit={(e) => {
          e.preventDefault();
          setParams(draft ? { q: draft } : {});
        }}
      >
        <input
          type="search"
          placeholder="Cari nama term…"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          style={{ maxWidth: 360 }}
          aria-label="Cari nama term"
        />
        <button type="submit">Cari</button>
        {data && <span className="muted">{data.total} term</span>}
      </form>
      <ErrorBanner message={error} />
      {loading && !data ? (
        <Loading />
      ) : data?.terms.length === 0 ? (
        <Empty>Tidak ada term{query && ` yang cocok dengan “${query}”`}.</Empty>
      ) : (
        data && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Nama</th>
                  <th>Deskripsi</th>
                  <th>Atribut</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.terms.map((term) => (
                  <tr key={term.id} className="clickable" onClick={() => navigate(`/terms/${term.id}`)}>
                    <td>
                      <Link to={`/terms/${term.id}`} onClick={(e) => e.stopPropagation()}>
                        <strong>{term.name}</strong>
                      </Link>
                      {!!term.synonyms?.length && (
                        <div className="muted" style={{ fontSize: 12 }}>
                          {term.synonyms.join(", ")}
                        </div>
                      )}
                    </td>
                    <td className="muted" style={{ maxWidth: 480 }}>
                      {term.description?.slice(0, 160)}
                      {(term.description?.length ?? 0) > 160 && "…"}
                    </td>
                    <td className="muted">
                      {count(data.column_attribute_counts, term.id)} kolom ·{" "}
                      {count(data.sql_attribute_counts, term.id)} SQL
                    </td>
                    <td>
                      <CertBadge value={term.certification} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
      {data && data.total > PAGE && (
        <div className="row" style={{ marginTop: 16 }}>
          <button
            disabled={skip === 0}
            onClick={() => setParams({ ...(query && { q: query }), skip: String(Math.max(0, skip - PAGE)) })}
          >
            ← Sebelumnya
          </button>
          <span className="muted">
            {skip + 1}–{Math.min(skip + PAGE, data.total)} dari {data.total}
          </span>
          <button
            disabled={skip + PAGE >= data.total}
            onClick={() => setParams({ ...(query && { q: query }), skip: String(skip + PAGE) })}
          >
            Berikutnya →
          </button>
        </div>
      )}
    </>
  );
}

export function TermDetail() {
  const { id } = useParams();
  const term = useFetch<S["DataResponse_TermDetail_"]>(`/terms/${id}`);
  const action = useAction();
  const t = term.data?.data;

  async function patch(body: S["TermUpdate"]) {
    const saved = await action.run(
      () => api<S["DataResponse_Term_"]>(`/terms/${id}`, { method: "PATCH", json: body }),
      "Tersimpan",
    );
    if (saved && t) term.setData({ data: { ...t, ...saved.data } });
  }
  const setCertification = (certification: string | null) =>
    t && term.setData({ data: { ...t, certification } });

  if (term.error) return <ErrorBanner message={term.error} />;
  if (!t) return <Loading />;

  return (
    <>
      <p>
        <Link to="/terms">← Semua term</Link>
      </p>
      <div className="row spread page-head">
        <h1>{t.name}</h1>
        <CertBadge value={t.certification} />
      </div>
      <ErrorBanner message={action.error} />

      <div className="card stack">
        <div className="row spread">
          <h3>Nama</h3>
          <CertifyCheck
            checked={t.name_certified}
            disabled={action.busy}
            onChange={(v) => patch({ name_certified: v })}
          />
        </div>
        <TextEditor value={t.name} rows={1} busy={action.busy} onSave={(name) => patch({ name })} />
        <div className="row spread">
          <h3>Deskripsi</h3>
          <CertifyCheck
            checked={t.description_certified}
            disabled={action.busy}
            onChange={(v) => patch({ description_certified: v })}
          />
        </div>
        <TextEditor value={t.description} rows={4} busy={action.busy} onSave={(description) => patch({ description })} />
        {!!t.synonyms?.length && (
          <div>
            <h3>Sinonim</h3>
            <div className="row">
              {t.synonyms.map((s) => (
                <span key={s} className="badge">
                  {s}
                </span>
              ))}
            </div>
          </div>
        )}
        {!!t.tables?.length && (
          <div>
            <h3>Tabel</h3>
            <div className="row">
              {t.tables.map((table) => (
                <Link key={table.id} to={`/catalog?table=${table.id}`} className="badge">
                  {table.name}
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>

      <ColumnAttributes termId={id!} onCertification={setCertification} />
      <SqlAttributes termId={id!} onCertification={setCertification} />
    </>
  );
}

function ColumnAttributes({ termId, onCertification }: { termId: string; onCertification: (c: string | null) => void }) {
  const list = useFetch<S["PagedListResponse_ColumnAttribute_"]>(`/terms/${termId}/column-attributes`);
  const action = useAction();

  async function patch(attr: S["ColumnAttribute"], body: S["ColumnAttributeUpdate"]) {
    const saved = await action.run(
      () =>
        api<S["ColumnAttributePatchResponse"]>(`/terms/${termId}/column-attributes/${attr.id}`, {
          method: "PATCH",
          json: body,
        }),
      "Tersimpan",
    );
    if (!saved || !list.data) return;
    list.setData({ ...list.data, data: list.data.data.map((a) => (a.id === attr.id ? saved.data : a)) });
    onCertification(saved.term_certification);
  }

  return (
    <section className="card">
      <h2>Atribut kolom {list.data && <span className="muted">({list.data.total})</span>}</h2>
      <ErrorBanner message={list.error ?? action.error} />
      {list.loading && !list.data && <Loading />}
      {list.data?.data.length === 0 && <Empty>Term ini belum punya atribut kolom.</Empty>}
      {!!list.data?.data.length && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Atribut</th>
                <th>Kolom sumber</th>
                <th style={{ width: "45%" }}>Deskripsi</th>
                <th>Review</th>
              </tr>
            </thead>
            <tbody>
              {list.data.data.map((attr) => (
                <tr key={attr.id}>
                  <td>
                    <strong>{attr.name}</strong>
                    <div className="muted mono">{attr.datatype}</div>
                  </td>
                  <td className="mono">
                    {attr.source_column}
                    {!!attr.sample_values?.length && (
                      <div className="muted" style={{ fontSize: 12 }}>
                        contoh: {attr.sample_values.slice(0, 5).join(", ")}
                      </div>
                    )}
                  </td>
                  <td>
                    <TextEditor
                      value={attr.description}
                      rows={2}
                      busy={action.busy}
                      onSave={(description) => patch(attr, { description })}
                    />
                  </td>
                  <td>
                    <div className="stack" style={{ gap: 6 }}>
                      <CertBadge value={attr.certified} />
                      <CertifyCheck
                        label="Certify"
                        checked={attr.certified}
                        disabled={action.busy}
                        onChange={(certified) => patch(attr, { certified })}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function SqlAttributes({ termId, onCertification }: { termId: string; onCertification: (c: string | null) => void }) {
  const list = useFetch<S["PagedListResponse_SqlAttribute_"]>(`/terms/${termId}/sql-attributes`);
  const [adding, setAdding] = useState(false);

  const replace = (attr: S["SqlAttribute"]) =>
    list.data && list.setData({ ...list.data, data: list.data.data.map((a) => (a.id === attr.id ? attr : a)) });

  return (
    <section className="card">
      <div className="row spread" style={{ marginBottom: 12 }}>
        <h2 style={{ margin: 0 }}>
          Atribut SQL {list.data && <span className="muted">({list.data.total})</span>}
        </h2>
        {!adding && <button onClick={() => setAdding(true)}>+ Tambah atribut SQL</button>}
      </div>
      <p className="muted">Ukuran atau metrik yang didefinisikan dengan ekspresi SQL, misalnya jumlah atau rasio.</p>
      <ErrorBanner message={list.error} />
      {adding && (
        <SqlAttributeForm
          termId={termId}
          onDone={(created) => {
            setAdding(false);
            if (created) list.reload();
          }}
        />
      )}
      {list.loading && !list.data && <Loading />}
      {list.data?.data.length === 0 && !adding && <Empty>Belum ada atribut SQL.</Empty>}
      <div className="stack">
        {list.data?.data.map((attr) => (
          <SqlAttributeCard
            key={attr.id}
            termId={termId}
            attr={attr}
            onChange={(a, certification) => {
              replace(a);
              if (certification !== undefined) onCertification(certification);
            }}
            onDeleted={list.reload}
          />
        ))}
      </div>
    </section>
  );
}

function SqlAttributeCard({
  termId,
  attr,
  onChange,
  onDeleted,
}: {
  termId: string;
  attr: S["SqlAttribute"];
  onChange: (attr: S["SqlAttribute"], certification?: string | null) => void;
  onDeleted: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const action = useAction();

  async function patch(body: S["SqlAttributeMetadataPatch"]) {
    const saved = await action.run(
      () => api<S["SqlAttributePatchResponse"]>(`/sql-attributes/${attr.id}`, { method: "PATCH", json: body }),
      "Tersimpan",
    );
    if (saved) onChange(saved.data, saved.term_certification);
  }

  async function remove() {
    if (!window.confirm(`Hapus atribut SQL “${attr.name}”?`)) return;
    const done = await action.run(() => api(`/sql-attributes/${attr.id}`, { method: "DELETE" }), "Dihapus");
    if (done !== undefined) onDeleted();
  }

  if (editing) {
    return (
      <SqlAttributeForm
        termId={termId}
        attr={attr}
        onDone={(saved) => {
          setEditing(false);
          if (saved) onChange(saved);
        }}
      />
    );
  }

  return (
    <div className="card" style={{ marginBottom: 0 }}>
      <div className="row spread">
        <div className="row">
          <strong>{attr.name}</strong>
          <CertBadge value={attr.certified} />
        </div>
        <div className="row">
          <CertifyCheck
            label="Certify"
            checked={attr.certified}
            disabled={action.busy}
            onChange={(certified) => patch({ certified })}
          />
          <button onClick={() => setEditing(true)}>Edit</button>
          <button className="danger" onClick={remove} disabled={action.busy}>
            Hapus
          </button>
        </div>
      </div>
      <ErrorBanner message={action.error} />
      <p style={{ marginTop: 8 }}>{attr.description || <span className="muted">Tanpa deskripsi.</span>}</p>
      {attr.description_suggestion && attr.description_suggestion !== attr.description && (
        <div className="card" style={{ borderStyle: "dashed" }}>
          <div className="muted" style={{ fontSize: 12 }}>
            Saran deskripsi
          </div>
          <p>{attr.description_suggestion}</p>
          <button disabled={action.busy} onClick={() => patch({ description: attr.description_suggestion })}>
            Terapkan saran
          </button>
        </div>
      )}
      <pre className="code">{attr.expression}</pre>
    </div>
  );
}

function SqlAttributeForm({
  termId,
  attr,
  onDone,
}: {
  termId: string;
  attr?: S["SqlAttribute"];
  onDone: (saved?: S["SqlAttribute"]) => void;
}) {
  const [name, setName] = useState(attr?.name ?? "");
  const [description, setDescription] = useState(attr?.description ?? "");
  const [expression, setExpression] = useState(attr?.expression ?? "");
  const [valid, setValid] = useState<boolean>();
  const action = useAction();

  async function validate() {
    const result = await action.run(() =>
      api<S["DataResponse_SqlExpressionValidationResult_"]>("/sql-attributes/validate", {
        method: "POST",
        json: { expression, term_id: termId, attribute_id: attr?.id ?? null },
      }),
    );
    if (result) setValid(result.data.valid);
  }

  async function save() {
    const body = { name, description, expression, term_id: termId };
    const saved = await action.run(
      () =>
        attr
          ? api<S["DataResponse_SqlAttribute_"]>(`/sql-attributes/${attr.id}`, { method: "PUT", json: body })
          : api<S["DataResponse_SqlAttribute_"]>("/sql-attributes", { method: "POST", json: body }),
      "Tersimpan",
    );
    if (saved) onDone(saved.data);
  }

  return (
    <div className="card stack">
      <label className="field">
        Nama
        <input value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <label className="field">
        Deskripsi
        <textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
      </label>
      <label className="field">
        Ekspresi SQL
        <span className="hint">Ekspresi agregat atas kolom tabel term ini, misalnya SUM(amount).</span>
        <textarea
          className="mono"
          rows={4}
          value={expression}
          onChange={(e) => {
            setExpression(e.target.value);
            setValid(undefined);
          }}
        />
      </label>
      <ErrorBanner message={action.error} />
      {valid === false && <div className="banner">Ekspresi tidak valid untuk tabel term ini.</div>}
      <div className="row">
        <button className="primary" onClick={save} disabled={action.busy || !name.trim() || !expression.trim()}>
          Simpan
        </button>
        <button onClick={validate} disabled={action.busy || !expression.trim()}>
          Validasi
        </button>
        {valid && <span className="badge solid">Valid</span>}
        <button onClick={() => onDone()} disabled={action.busy}>
          Batal
        </button>
      </div>
    </div>
  );
}
