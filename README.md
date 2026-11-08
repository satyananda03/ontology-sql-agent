<!--
SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
SPDX-License-Identifier: Apache-2.0
-->

# Ontology SQL Agent

Answers questions about a PostgreSQL warehouse with SQL. An ontology of the
warehouse picks the relevant tables and supplies what the SQL generator should
know about them:

- business terms;
- column descriptions;
- join paths;
- definitions;
- synonyms.

A calling agent asks through one HTTP endpoint and gets back rows, or a
reason why there are none.

| Directory | What it is |
| --- | --- |
| `auto_ontology/` | A trimmed fork of [NVIDIA Auto-Ontology](https://github.com/NVIDIA/auto-ontology). It holds the ontology store (Postgres + pgvector), ingestion, compilation of the semantic layer, retrieval, and the API a review UI edits the ontology through. |
| `ontology_sql_agent/` | The SQL agent: the classic SQL agent's graph, with table selection done by the ontology. It is served at `POST /api/sql-agent/query`. |
| `alembic/` | Migrations for the store schema |
| `dev_tools/` | Test fixtures and the OpenAPI generator |
| `docs/` | The endpoint, connections, OpenAPI specs, and the changes from upstream |

## Run with Docker

```bash
cp .env.example .env                 # store, models, CONNECTION_STRINGS, SQL_AGENT_API_KEY
cp ingest.example.yaml ingest.yaml   # which schemas and tables to ingest
make up                              # postgres, migrate, backend :3001, ingestion :3002
```

The ingestion service ingests the catalog at startup. Then compile the semantic
layer (terms, attributes and join paths) once per database:

```bash
docker compose exec backend python -m auto_ontology.semantic --database-name <db>
```

Ask a question:

```bash
curl -s localhost:3001/api/sql-agent/query \
  -H "x-api-key: $SQL_AGENT_API_KEY" -H "content-type: application/json" \
  -d '{"question": "berapa jumlah peserta program tahun 2024?"}'
```

[`docs/sql-agent-tool.md`](docs/sql-agent-tool.md) covers the response, its
configuration, and a FastMCP tool that wraps the endpoint.

## Run from source

```bash
uv sync
make migrate
make ingest-dev    # terminal 1: ingestion service on :3002
make backend-dev   # terminal 2: FastAPI on :3001 with hot reload
```

## Reviewing the ontology

`ui/` is a small React app (Vite, no Next.js) for the people who keep the
ontology right. With the backend running:

```bash
make ui            # http://127.0.0.1:5173
```

| Page | What it is for |
|---|---|
| Terms | Certify a term's name and description, its column attributes and SQL attributes; add or edit SQL attributes |
| Katalog | Edit and certify table and column descriptions |
| Pencarian | Find any term, table, column, attribute or analysis |
| Glossary | Acronyms and internal terms the agent reads on every question |
| Custom analyses | Verified question-and-SQL examples the agent retrieves as references |
| Koneksi | Source databases; saving one starts ingestion |
| Pengaturan | Scheduled compilation, value probing, PII detection, the SQL timeout; run or reset compilation; export and import the model |
| Playground | Ask `POST /api/sql-agent/query` and see exactly what an MCP caller gets |

"Human review" is the `certified` flag on each field, as upstream: a term rolls
up to pending, partial or certified from its own fields and its attributes.

**There is no login.** The backend trusts its caller (the
`x-auto-ontology-user-id` header is never checked, and the UI does not send it),
so the UI, the backend and the ingestion service listen on `127.0.0.1` only,
and `docker-compose.yml` binds their ports there. The Vite dev server adds
`x-api-key` from `.env` to `/api/sql-agent/*` requests, so the key never reaches
the browser. Request and response types are generated from
`docs/openapi/backend.json` whenever the UI starts or builds.

## Tests

```bash
make lint
make test
```

The DAL golden tests skip unless a seeded fixture is reachable; see
[`dev_tools/README.md`](dev_tools/README.md). Measure answer quality with
`make eval` and `make eval-report`, which are described in
[`docs/sql-agent-tool.md`](docs/sql-agent-tool.md).

## License

Apache-2.0; see [`LICENSE`](LICENSE). Third-party components are listed in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
[`docs/changes-from-upstream.md`](docs/changes-from-upstream.md) lists what
differs from Auto-Ontology.
