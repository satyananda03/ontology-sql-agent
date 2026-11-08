# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Ask the golden questions through the classic agent, as a baseline.

It lives in another application, so run this from there and pass absolute paths::

    cd ~/iccn-dashboard-knowledge && PYTHONPATH=. .venv/bin/python \\
        ~/ontology-sql-agent/sql_agent/eval/classic_arm.py --golden <yaml> --out <jsonl>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

import yaml


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    from app.tools.search.database.sql_agent.nodes import schema_navigator
    from app.tools.search.database.sql_agent.workflow import sql_agent_graph

    questions = yaml.safe_load(args.golden.read_text())["questions"][: args.limit]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as out:
        for item in questions:
            schema_navigator._SCHEMA_CACHE.clear()
            started = time.monotonic()
            sql, error, tables = "", "", []
            try:
                state = await asyncio.wait_for(
                    sql_agent_graph.ainvoke(
                        {
                            "messages": [],
                            "user_query": item["question"],
                            "access_tag": "public",
                        },
                        config={"recursion_limit": 50},
                    ),
                    timeout=200,
                )
                sql = str(state.get("sql_query") or "")
                error = str(state.get("error") or "")
                tables = state.get("selected_table") or []
            except Exception as exc:  # noqa: BLE001 — one failure must not end the run
                error = f"{type(exc).__name__}: {exc}"
            record = {
                "id": item["id"],
                "arm": "classic",
                "sql": sql,
                "error": error,
                "seconds": round(time.monotonic() - started, 1),
                "llm_calls": None,
                "input_tokens": None,
                "context_tables": tables,
            }
            out.write(json.dumps(record) + "\n")
            out.flush()
            print(f"{item['id']}: {record['seconds']}s", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
