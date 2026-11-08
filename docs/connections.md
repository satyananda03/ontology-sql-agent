<!--
SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES.
All rights reserved.
SPDX-License-Identifier: Apache-2.0
-->

# The source database

Exactly one PostgreSQL source database, read from the `CONNECTION_STRINGS`
environment variable (`.env` for Docker Compose):

```bash
CONNECTION_STRINGS=postgresql://reader:password@localhost:5432/sales_db
```

Both the backend and the ingestion service refuse to start when it holds more
than one URL. To switch databases, change it and restart both. `GET /api/connection`
shows it without the password; the review UI's Koneksi page reads that.

The URL carries no schema or table filters of its own; use `ingest.yaml` below.
`source_connection_string()` in
[`auto_ontology/connectors/registry.py`](../auto_ontology/connectors/registry.py)
is the one place it is read.

## Limit ingestion with `ingest.yaml`

To ingest only part of a database, copy `ingest.example.yaml` to `ingest.yaml` at
the repo root (or point `INGEST_CONFIG_FILE` at it):

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
