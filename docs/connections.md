<!--
SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES.
All rights reserved.
SPDX-License-Identifier: Apache-2.0
-->

# Connections and credential storage

Source databases are PostgreSQL only. The backend reads them from two places:
connections stored through the API, and the `CONNECTION_STRINGS` environment
variable. Use one per deployment, because the two code paths order them
differently:

- **Answering questions** uses stored connections when any exist, and falls
  back to `CONNECTION_STRINGS`.
- **Ingestion** uses `CONNECTION_STRINGS` whenever it's set, and reads stored
  connections only when it's empty.

## Connections stored through the API

Add a connection with `POST /api/connections/test`, then `POST /api/connections`
(permission `connection:manage`).

Each connection can carry `table_allow_regex` / `table_deny_regex`, applied at
catalog extraction. Deny wins, and names are unqualified and case-sensitive.
Schemas are scoped with `ingest.yaml`, below.

Where the credentials live depends on whether Vault is configured:

- **Without Vault.** The full connection object, password included, is
  serialized to JSON and stored unencrypted on the catalog's database row in
  Postgres.
- **With Vault.** Credentials are written to Vault, keyed by database name, and
  the catalog row stores none. The database name is the lookup key.

## `CONNECTION_STRINGS`

A comma- or newline-separated list of connection URLs supplied at deploy time
(`.env` for Docker Compose). It carries
no schema or table filters of its own; use `ingest.yaml` below. `GET /api/connections/source`
reports whether it is set.

Use a `postgresql://` or `postgres://` URL. The registry lives in
[`auto_ontology/connectors/registry.py`](../auto_ontology/connectors/registry.py).

## Limit ingestion with `ingest.yaml`

To ingest only part of a database, copy `ingest.example.yaml` to `ingest.yaml` at
the repo root (or point `INGEST_CONFIG_FILE` at it). It applies whichever way the
connection was added:

```yaml
databases:
  sales_db:
    schemas: [analytics]
    exclude_tables: [tmp_import]
```

`sales_db` is the database name from the connection. A database the file doesn't
list is ingested in full. Ingestion fails if a listed schema has no readable tables,
because ingest deletes catalog schemas it no longer sees.

The file limits what goes into the catalog. It isn't an access control: to stop
queries reaching other schemas, connect with a database role that can't read them.

## Vault

Vault is off by default. It turns on only when all four of these are set:

- `VAULT_ADDR`
- `VAULT_NAMESPACE`
- `VAULT_ROLE_ID`
- `VAULT_SECRET_ID`

`VAULT_AUTH_MOUNT` and `VAULT_KV_MOUNT` are optional overrides. A partial
configuration is ignored with a warning, and credentials fall back to plaintext
storage in Postgres.
