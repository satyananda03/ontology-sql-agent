<!--
SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES.
All rights reserved.
SPDX-License-Identifier: Apache-2.0
-->

# dev_tools

Local development helpers: test fixtures, a one-shot ingest, and the OpenAPI
generator.

| Path | What it is |
|---|---|
| `fixtures/` | Builds the databases the golden and connector tests replay against |
| `local_ingest.py` | Ingests the first `CONNECTION_STRINGS` database into the pgvector store, without the ingestion service |
| `generate_backend_openapi.py` | Writes the FastAPI specs to `docs/openapi/`; `tests/test_openapi.py` fails when they are stale |
| `_add_spdx_headers.py` | Adds SPDX headers to files that lack them |
| `tests/` | Licensing, packaging and OpenAPI checks |

## Fixtures

`auto_ontology/dal/tests/test_golden.py` and
`auto_ontology/connectors/tests/test_postgres.py` replay against the pagila
fixture, so changing a fixture changes what those tests prove. See
[`fixtures/sql/README.md`](./fixtures/sql/README.md) for what the fixture covers.

The golden tests skip unless a seeded fixture is reachable. Run them against a
local Postgres, never against a shared store: `seed_graph_fixture --reset` wipes
the store it points at.

```bash
docker compose up -d postgres
uv run --no-sync alembic upgrade head
uv run --no-sync python -m dev_tools.fixtures.seed_fixtures
CONNECTION_STRINGS=postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@localhost:$POSTGRES_PORT/pagila \
  uv run --no-sync python -m dev_tools.fixtures.seed_graph_fixture --reset
uv run --no-sync pytest -q
```

Re-record the golden only when a change to DAL output is intended:

```bash
uv run --no-sync python -m dev_tools.fixtures.capture_dal_golden
```
