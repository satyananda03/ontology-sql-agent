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

A review UI is not part of this repository. The backend serves everything one
needs under `/api/`:

- terms, attributes and SQL attributes;
- tags, rules and zones;
- users and groups;
- search.

[`docs/openapi/backend.json`](docs/openapi/backend.json) describes them all. A UI
should know three things:

- **Authentication.** The backend trusts the `x-auto-ontology-user-id` header
  set by the gateway in front of it. Expose the backend only through that
  gateway.
- **The glossary.** It is read from `frontend.acronyms`. Until a UI creates that
  table, questions run with an empty glossary.
- **Scheduled compilation.** It is off until `semantic_compilation_enabled` is
  set in `frontend.configurations`. Run the compile command above by hand until
  then.

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
