<!--
SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
SPDX-License-Identifier: Apache-2.0
-->

# Changes from upstream Auto-Ontology

`auto_ontology/` started from [NVIDIA/auto-ontology](https://github.com/NVIDIA/auto-ontology)
at commit `caced11e`. It stays close to upstream, so its tested logic remains intact
and upstream fixes can still be ported. New behavior belongs in `sql_agent/`.
This file lists every change made inside `auto_ontology/`.

## Removed

| Part | Notes |
| --- | --- |
| Chat: `server/chat`, `retrieval/text_to_sql/main.py`, `text_to_sql_graph.py`, the full agent graph's nodes and the visualization agent | The SQL agent replaces the chat pipeline. `settings_dal.py` moved to `server/settings_dal.py`, without the visualization flag. |
| PQL analyses and Kumo: `server/pql_analyses`, `retrieval/kumo`, `dal/pql_analyses.py` | The PQL tables stay in the store schema, because applied migrations are never edited. |
| The interactive clarification agent: `retrieval/interactive` | |
| Every connector except PostgreSQL | ClickHouse, Databricks, DuckDB, HeavyDB, Kyuubi, MySQL, Snowflake, SQLite and Trino, with their drivers and the Databricks SSO route. |
| The LLM intent check and the db_probe pre-execution checks | Only `ProbeExecutor` remains, for semantic foreign-key inference. |
| `frontend/`, `mcp/`, `helm/`, `vendor/` and the CI workflows | The review UI is rebuilt separately. |
| `dev_tools/`: fixtures, the one-shot ingest, the SPDX helper, the licensing and packaging tests; with them `dal/tests/test_golden.py`, `dal/tests/golden/` and `connectors/tests/test_postgres.py`, which ran only against those fixtures | The OpenAPI generator moved to `sql_agent/openapi.py` (`make openapi`). |
| Apache Ossie model export/import: the `ossie` model format, `include_ontology`, and the `apache-ossie-nvidia-auto-ontology` dependency | Only the native Auto Ontology YAML is exported and imported. A file whose root holds none of its keys is rejected with 422 rather than read as an empty model. |

Definitions left unreferenced by these removals were removed as well. Notable
consequences:

- **No `schemas` allowlist on a connection.** The PostgreSQL connector never
  honored it; only the removed engines did. Scope ingestion with `ingest.yaml`
  instead.
- **Smaller DAL golden.** The Chinook (SQLite) fixture is gone, and so is
  golden coverage of cross-database join paths and of a zone that spans two
  databases. The second fixture zone is now "Schema and table": a schema plus a
  table from another schema in the same database.

## Changed

| File | Change | Why |
| --- | --- | --- |
| `connectors/postgres.py` | `get_pks` and `get_fks` read `pg_constraint` | A read-only role saw no keys through `information_schema` |
| `connectors/postgres.py` | `get_tables` and `get_columns` read `COMMENT ON` | A written comment is used instead of an LLM guess |
| `catalog/extract.py`, `catalog/ingest_config.py` | Optional `ingest.yaml` scope | Ingest only the schemas that matter |
| `utils/embedding.py`, `vdb/postgres.py`, `utils/llm_invoke.py` | Configurable vector size, request fields and concurrency | Models served through a gateway |
| `semantic/deterministic.py`, `dal/attributes.py` | `vector` columns get no attribute and skip foreign-key inference | They add noise to retrieval and are never join keys |
| `semantic/embed.py` | A Term's embedded text includes its synonyms | A question using a synonym can find the Term |
| `semantic/visit_enter.py` | `LOW_CARDINALITY_MAX` sets the full-value limit, default still 25 | Province lists exceed 25 values |
| `server/__main__.py` | Registers the `sql_agent` router; no chat worker pool | `POST /api/sql-agent/query` |
| `connectors/registry.py` | `source_connection_string()`: the connector comes from `CONNECTION_STRINGS` only, which must hold exactly one URL. Stored connections are no longer read | This build answers from a single source database |
| `ingestion_service/connections.py`, `ingestion_service/data_scheduler.py` | Resolve the connection through `source_connection_string()` | Same |
| `ingestion_service/scheduler.py`, `data_scheduler.py`, `semantic_scheduler.py`, `__main__.py` | `OnDemandScheduler` replaces `IntervalScheduler`: no startup run and no 24h timer. Both jobs share one lock, so ingest and compilation never overlap. An ingest pass always replays the tagging rules | Ingest, compilation and regeneration run only from the review UI's buttons |
| `ingestion_service/config.py` (removed), `server/settings/router.py` | The `semantic_compilation_enabled` flag is gone; a triggered compilation always runs | It only switched the schedule on, and while off it made the compile button do nothing |
| `ingestion_service/router.py`, `server/ingestion/proxy.py`, `server/responses.py` | New `POST /ingest/run` and `GET /ingest/status`; `/semantic/compile` only triggers | The backend's `POST /api/ingest` and `GET /api/ingest/status` (in `sql_agent/server/connection.py`) relay them |
| `server/__main__.py`, `ingestion_service/__main__.py` | Listen on `BIND_HOST`, default `127.0.0.1` instead of `0.0.0.0` | Neither has a login; a container sets `BIND_HOST=0.0.0.0` |
| `server/__main__.py`, `ingestion_service/__main__.py` | Refuse to start when `CONNECTION_STRINGS` holds more than one URL. The backend mounts the read-only `GET /api/connection` instead of the `/api/connections` routes | Same. The regex table filter of a stored connection goes with them; `ingest.yaml` `exclude_tables` covers it |
| `server/connections/service.py` | Connection edits refresh only the connector cache | The chat worker it also refreshed is gone |
| `server/users/permissions.py` | `access.json` in the package is the source of truth | It used to be generated from `frontend/auth/access.json` |
| `version.py` | Reads the `ontology-sql-agent` distribution | The package was renamed |
| `server/settings/router.py`, `server/settings_dal.py` | New `/api/acronyms` CRUD and `GET/PATCH /api/settings` | Upstream wrote the glossary and flags from Next.js through Prisma |
| `alembic/versions/5d2e8b7c41af_*` | Creates `frontend.configurations` and `frontend.acronyms` when absent | A fresh database has no Prisma to create them; an existing store is left as it is |
| `docker-compose.yml` | Ports bound to `127.0.0.1` | The review UI has no login and the backend trusts its caller |

## The SQL agent compared with `classic_sql_agent`

`sql_agent/` is a port of the classic SQL agent. These are the deliberate
differences from the original:

| Part | Original | Now | Why |
| --- | --- | --- | --- |
| Table selection | The schema navigator reads every table's catalog | `ontology_context` runs auto_ontology's retrieval and graph search | Context no longer grows with the number of tables |
| Knowledge | Hand-written YAML dictionary | The ontology store: descriptions, join paths, definitions, synonyms and the glossary | One source of truth, generated and then reviewed |
| Generator prompt | Values only from "Nilai persis"; joins only from declared keys | Adds an `<ontology_knowledge>` block, accepts its join paths, and falls back to `ILIKE` when a needed value is missing from the samples | Sample values can be incomplete |
| Generator limits | 700 output tokens | 2000; model from `SQL_AGENT_GENERATOR_MODEL` | A multi-join query could be cut off |
| Semantic search | Top 20 ids; filters chosen by the navigator | `semantic_rows`, which plans its own filters | The 20-id limit undercounted larger topics |
| Safety | Keyword regex plus access tags | The parsed statement must be a single read-only query | The regex rejected `ILIKE '%update%'`; access control is the database role's job |
| Syntax check | asyncpg `PREPARE` | `EXPLAIN` through the auto_ontology connector | One read-only connection and timeout for every node |
| Execution | Async SQLAlchemy | Synchronous nodes on the same connector | Retrieval is synchronous, so async only added bridging |
