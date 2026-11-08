<!--
SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
SPDX-License-Identifier: Apache-2.0
-->

# The SQL agent endpoint

`POST /api/sql-agent/query` answers one standalone question from the database.
A calling agent reaches it through a tool, such as the FastMCP example below.
Keep the backend port private, because this endpoint runs SQL that the agent
writes.

## How a question is answered

The graph lives in `sql_agent/workflow.py`:

1. **`ontology_context`** runs auto_ontology's retrieval (`sql_agent/retrieval.py`):
   - entity extraction;
   - vector search over Terms and columns;
   - graph search for join paths.

   The result is the chosen tables, their schema, and an `<ontology_knowledge>`
   block with column descriptions, join paths, business definitions, synonyms
   and the glossary.
2. **`semantic_search`** matches free-text topics against the warehouse's
   `*_vector` columns. The matching row ids reach the SQL through a
   placeholder, so the LLM never copies them.
3. **`sql_generator`** writes one PostgreSQL query.
4. **`sql_safety_validator`** accepts only a single read-only query. It checks
   the parsed statement, not keywords.
5. **`sql_syntax_validator`** runs `EXPLAIN`.
6. **`sql_executor`** runs the query on the read-only connection.

When something goes wrong:

- A repairable error goes back to the generator. All repairs share a budget of
  two retries.
- An empty result triggers a probe of the filtered values first.
- When the chosen tables prove insufficient, retrieval runs again, up to
  `SQL_AGENT_MAX_RENAVIGATIONS` times.

## Request

```http
POST /api/sql-agent/query
x-api-key: <SQL_AGENT_API_KEY>
Content-Type: application/json

{"question": "siapa saja researcher di bidang pariwisata"}
```

| Field | Required | Meaning |
| --- | --- | --- |
| `question` | Yes | A standalone question. The caller resolves follow-ups first. |
| `evidence` | No | Rules the SQL must follow. |

A missing or wrong key returns 401. If the server has no `SQL_AGENT_API_KEY`
set, every request returns 503.

## Response

```json
{"status": "ok", "text": "ROWS : 4\n...", "sql": "SELECT ...", "row_count": 4, "truncated": false}
```

Pass `text` to the agent unchanged: it tells the agent what to do next.

| `status` | Meaning | What the agent should do |
| --- | --- | --- |
| `ok` | Rows came back | Answer from them |
| `empty` | The query ran and matched nothing | Retry once with other terms, then report no data |
| `unanswerable` | No query could be written | Report that the data is not available |
| `error` | A server or database failure | Retry once, then report the outage |

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `SQL_AGENT_API_KEY` | none | Required. The key callers send in `x-api-key`. |
| `SQL_AGENT_GENERATOR_MODEL` | `qwen.qwen3-coder-480b-a35b-v1:0` | Generator model, served by `REASONING_ENDPOINT` |
| `SQL_AGENT_MAX_ROWS` | 200 | Rows shown to the calling agent |
| `SQL_AGENT_TIMEOUT_S` | 120 | Seconds before the request reports a timeout |
| `SQL_AGENT_MAX_CONCURRENT` | 4 | Questions answered at once |
| `SQL_AGENT_MAX_RENAVIGATIONS` | 1 | Extra retrieval rounds |

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
            f"{os.environ['SQL_AGENT_URL']}/api/sql-agent/query",
            headers={"x-api-key": os.environ["SQL_AGENT_API_KEY"]},
            json={"question": question},
        )
    response.raise_for_status()
    return response.json()["text"]
```

## Knowledge and evaluation

| Command | What it does |
| --- | --- |
| `uv run python -m sql_agent.knowledge.import_classic_yaml --dictionary <yaml>` | Imports the classic agent's hand-written dictionary into the ontology. It prints the changes and writes only with `--apply`. |
| `uv run python -m sql_agent.knowledge.generate_synonyms propose --out synonyms.yaml` | Proposes Term synonyms for review. `apply synonyms.yaml` writes the reviewed file. |
| `make eval` | Asks the questions in `sql_agent/eval/golden.yaml` and records each one's SQL, time and LLM usage in `runs/agent.jsonl`. Row data is never stored. |
| `make eval-report` | Scores every run file in `runs/` against the golden SQL, using a read-only session. |

`sql_agent/eval/classic_arm.py` asks the same questions through the
original classic agent. That agent is a separate application, so the script runs
from that application's checkout.
