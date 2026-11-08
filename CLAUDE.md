<!--
SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
SPDX-License-Identifier: Apache-2.0
-->

# Ontology SQL Agent

A PostgreSQL text-to-SQL agent (`ontology_sql_agent/`) on a trimmed fork of NVIDIA
Auto-Ontology (`auto_ontology/`). See `README.md` for the layout.

## Dev commands

Run from the repo root:

| Command | Description |
|---|---|
| `make backend-dev` | FastAPI on :3001 with hot reload (`create_app()` in `auto_ontology/server/__main__.py`) |
| `make ingest-dev` | Ingestion service on :3002 |
| `uv run python -m auto_ontology.semantic --database-name <db>` | Compile the semantic layer for one database |
| `make eval` / `make eval-report` | Golden-question evaluation; never stores row data |

## Rules

- **Where code goes.** New behavior belongs in `ontology_sql_agent/`. Keep
  `auto_ontology/` close to upstream, and record every change inside it in
  `docs/changes-from-upstream.md`.
- **The store is Postgres.** `auto_ontology/dal/` queries it with SQLAlchemy
  Core (no ORM).
  - `dal/schema.py` is the single source of truth for the schema.
  - `dal/session.py` owns the pooled engine.
  - Schema changes go through Alembic (`make migrate-revision m="..."`). Never
    hand-edit a migration that has been applied.
  - Read the comments in `schema.py` before changing a table.
- **Source databases are PostgreSQL only.** Schemas are scoped by `ingest.yaml`;
  the connection's table regexes filter tables.
- **SQL agent safety.** The agent executes only a single parsed read-only query
  (`nodes/safety_validator.py`). The database role it connects with is the real
  access control.
- **Dependencies.** Add them with `uv add`, never pip, and don't edit
  `pyproject.toml` by hand for dependencies. Add a row to
  `THIRD_PARTY_NOTICES.md` in the same change.
- **Type hints** are required on all function signatures.
- **Exception handlers.** Use plain `def`, not `async def`, for
  `@app.exception_handler` functions.

## Before committing

| Check | Command |
|---|---|
| Lint and format | `make lint` (fix with `uv run ruff check --fix` and `uv run ruff format`) |
| Tests | `make test` |
| OpenAPI | `uv run python -m dev_tools.generate_backend_openapi` |
| Review UI | `make ui-build` (type-checks against the regenerated OpenAPI types) |

The OpenAPI specs in `docs/openapi/` embed each route's docstring. Editing a
docstring on any `@router` handler makes them stale, and
`dev_tools/tests/test_openapi.py` fails until you regenerate and commit them.

Run tests that touch a database against a local or throwaway Postgres, never a
shared store: `seed_graph_fixture --reset` wipes the store it points at.

## Git

Commit messages are concise and imperative, with no `Co-Authored-By`
trailers. Branch from `main`.
