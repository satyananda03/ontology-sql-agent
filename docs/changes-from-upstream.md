<!--
SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
SPDX-License-Identifier: Apache-2.0
-->

# Changes from upstream Auto-Ontology

`auto_ontology/` started from [NVIDIA/auto-ontology](https://github.com/NVIDIA/auto-ontology)
at commit `caced11e`. It stays close to upstream, so its tested logic remains intact
and upstream fixes can still be ported. New behavior belongs in `ontology_sql_agent/`.
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

Definitions left unreferenced by these removals were removed as well. Notable
consequences:

- **No `schemas` allowlist on a connection.** The PostgreSQL connector never
  honored it; only the removed engines did. Scope ingestion with `ingest.yaml`
  instead. `POST /api/connections/test` still returns `schemas`, now always
  empty.
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
| `server/__main__.py` | Registers the `ontology_sql_agent` router; no chat worker pool | `POST /api/sql-agent/query` |
| `server/connections/service.py` | Connection edits refresh only the connector cache | The chat worker it also refreshed is gone |
| `server/users/permissions.py` | `access.json` in the package is the source of truth | It used to be generated from `frontend/auth/access.json` |
| `version.py` | Reads the `ontology-sql-agent` distribution | The package was renamed |

## The SQL agent compared with `classic_sql_agent`

`ontology_sql_agent/` is a port of the classic SQL agent. These are the deliberate
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
