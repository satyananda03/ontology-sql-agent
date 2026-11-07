<!--
SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
SPDX-License-Identifier: Apache-2.0
-->

# `search_database_knowledge` tool

The lightweight question-answering path for a calling agent. The tool is registered
in a separate FastMCP server, which calls this endpoint over HTTP. Keep the backend
port private: the endpoint runs agent-written SQL.

Two pipelines can answer, chosen with `ONTO_SQL_PIPELINE`: `classic` (the default, in
`onto_sql/classic/`) and `lite` (in `onto_sql/pipeline/`). The request and response
below are the same for both.

## Request

```http
POST /api/sql-agent/query
x-api-key: <ONTO_SQL_API_KEY>
Content-Type: application/json

{"question": "siapa saja researcher di bidang pariwisata"}
```

| Field | Required | Meaning |
| --- | --- | --- |
| `question` | Yes | A standalone question. The caller resolves follow-ups first. |
| `target_db` | No | Database to query, when several are connected. |
| `evidence` | No | Rules the SQL must follow. |

A missing or wrong key returns 401, and a server without `ONTO_SQL_API_KEY` returns 503.

## Response

```json
{"status": "ok", "text": "ROWS : 4\n...", "sql": "SELECT ...", "row_count": 4, "truncated": false}
```

Pass `text` to the agent as it is. It tells the agent what to do next.

| `status` | Meaning | What the agent should do |
| --- | --- | --- |
| `ok` | Rows came back | Answer from them |
| `empty` | The query ran and matched nothing | Retry once with other terms, then report no data |
| `unanswerable` | No query could be written | Report that the data is not available |
| `error` | A server or database failure | Retry once, then report the outage |

## FastMCP tool

```python
import os

import httpx
from fastmcp import FastMCP

mcp = FastMCP("database-knowledge")


@mcp.tool
async def search_database_knowledge(question: str) -> str:
    """Query structured database records with a standalone question."""
    async with httpx.AsyncClient(timeout=130) as client:
        response = await client.post(
            f"{os.environ['ONTO_SQL_URL']}/api/sql-agent/query",
            headers={"x-api-key": os.environ["ONTO_SQL_API_KEY"]},
            json={"question": question},
        )
    response.raise_for_status()
    return response.json()["text"]
```
