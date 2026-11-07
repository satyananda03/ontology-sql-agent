<!--
SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
SPDX-License-Identifier: Apache-2.0
-->

# Changes to `auto_ontology/`

onto-sql keeps `auto_ontology/` close to upstream so its tested logic stays intact and
updates can still be merged. New behavior belongs in `onto_sql/`. This file lists every
change made inside `auto_ontology/` since upstream commit `caced11e`.

| File | Change | Why |
| --- | --- | --- |
| `connectors/postgres.py` | `get_pks` and `get_fks` read `pg_constraint` | A read-only role saw no keys through `information_schema` |
| `catalog/extract.py`, `catalog/ingest_config.py` | Optional `ingest.yaml` scope | Ingest only the schemas that matter |
| `utils/embedding.py`, `vdb/postgres.py`, `utils/llm_invoke.py` | Configurable vector size, request fields and concurrency | Models served through a gateway |
| `retrieval/text_to_sql/main.py` | `stream_agent_response` takes an optional `compiled_graph` | Run the lightweight graph through the same driver |
| `server/__main__.py` | Registers the `onto_sql` router | `POST /api/sql-agent/query` |
| `semantic/deterministic.py`, `dal/attributes.py` | `vector` columns get no attribute and skip foreign key inference | They add noise to retrieval and are never join keys |
| `semantic/embed.py` | A Term's embedded text includes its synonyms | A question using a synonym can find the Term |
| `semantic/visit_enter.py` | `LOW_CARDINALITY_MAX` sets the full-value limit, default still 25 | Province lists exceed 25 values |
| `connectors/postgres.py` | `get_tables` and `get_columns` read `COMMENT ON` | A written comment is used instead of an LLM guess |

## Classic pipeline (`onto_sql/classic/`)

Ported from `classic_sql_agent`. These are the deliberate differences from the original:

| Part | Original | Now | Why |
| --- | --- | --- | --- |
| Table selection | Schema navigator reads every table's catalog | `ontology_context` runs auto_ontology's retrieval and graph search | Context no longer grows with the number of tables |
| Knowledge | Hand-written YAML dictionary | Ontology store: descriptions, join paths, definitions, synonyms, glossary | One source of truth, generated then reviewed |
| Generator prompt | Values from "Nilai persis" only, joins from declared keys | Adds an `<ontology_knowledge>` block, accepts its join paths, and falls back to ILIKE when a needed value is missing from the samples | Sample values can be incomplete |
| Generator limits | 700 output tokens | 2000, model from `ONTO_SQL_GENERATOR_MODEL` | A multi-join query could be cut off |
| Semantic search | Top 20 ids, filters chosen by the navigator | `onto_sql.pipeline.semantic_rows`, which plans its own filters | The 20-id limit undercounted larger topics |
| Safety | Keyword regex plus access tags | Parsed statement must be a single read-only query | The regex rejected `ILIKE '%update%'`; access is the database role's job |
| Syntax check | asyncpg `PREPARE` | `EXPLAIN` through the auto_ontology connector | One read-only connection and timeout for every node |
| Execution | Async SQLAlchemy | Synchronous nodes on the same connector | Retrieval is synchronous, so async only added bridging |

