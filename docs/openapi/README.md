<!--
SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES.
All rights reserved.
SPDX-License-Identifier: Apache-2.0
-->

# OpenAPI specs

Generated files: do not edit them by hand. They are committed so that API changes
show up in review and the specs can be read without a running server.

| File | Describes |
| --- | --- |
| [`backend.json`](./backend.json) | The FastAPI backend on :3001, including `POST /api/sql-agent/query` |
| [`ingestion.json`](./ingestion.json) | The ingestion service on :3002 |

The spec embeds each route's docstring. Regenerate both specs whenever a route's
signature, models or docstring changes:

```sh
uv run python -m dev_tools.generate_backend_openapi
```

The API is snake_case throughout: path segments, parameters, request bodies and
response fields.
