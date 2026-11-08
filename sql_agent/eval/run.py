# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Ask the golden questions through the agent and record what it did.

Stores the SQL, time, LLM usage and tables in context, never the rows::

    uv run python -m sql_agent.eval.run --out runs/agent.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

GOLDEN = Path(__file__).with_name("golden.yaml")
ARM = "agent"
_LLM_ENTRY_POINTS = (
    "invoke_with_structured_output",
    "safe_invoke_with_structured_output",
)


class Usage:
    """LLM calls, their time and approximate input tokens for one question."""

    def __init__(self) -> None:
        self.calls = 0
        self.input_tokens = 0
        self.llm_seconds = 0.0
        self.context_tables: list[str] = []

    def reset(self) -> None:
        self.__init__()

    def count(self, function: Callable[..., Any]) -> Callable[..., Any]:
        def counted(llm: Any, messages: list, *args: Any, **kwargs: Any) -> Any:
            self.calls += 1
            text = sum(len(str(getattr(m, "content", m))) for m in messages)
            self.input_tokens += text // 4
            started = time.monotonic()
            try:
                return function(llm, messages, *args, **kwargs)
            finally:
                self.llm_seconds += time.monotonic() - started

        return counted


def _instrument(usage: Usage) -> None:
    from auto_ontology.retrieval.text_to_sql.agents.candidates_preparation import (
        CandidatePreparationAgent,
    )

    for name, module in list(sys.modules.items()):
        if not name.startswith(("auto_ontology.", "sql_agent.")) or (
            "llm_invoke" in name
        ):
            continue
        for entry in _LLM_ENTRY_POINTS:
            if callable(getattr(module, entry, None)):
                setattr(module, entry, usage.count(getattr(module, entry)))

    prepare = CandidatePreparationAgent.execute

    def record_tables(self: Any, state: Any) -> dict[str, Any]:
        result = prepare(self, state)
        tables = result.get("path_state", {}).get("relevant_tables") or []
        usage.context_tables = [t.get("name", "") for t in tables]
        return result

    CandidatePreparationAgent.execute = record_tables


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--golden", type=Path, default=GOLDEN)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    load_dotenv(Path.cwd() / ".env")

    # Imported before _instrument, which wraps the LLM calls of loaded modules.
    from sql_agent.service import run

    def answer(question: str) -> tuple[str, str]:
        """Return ``(sql, error)`` for one question."""
        state = run(question)
        return state.get("sql_query") or "", state.get("error") or ""

    usage = Usage()
    _instrument(usage)
    questions = yaml.safe_load(args.golden.read_text())["questions"][: args.limit]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as out:
        for item in questions:
            usage.reset()
            started = time.monotonic()
            sql, error = answer(item["question"])
            record = {
                "id": item["id"],
                "arm": ARM,
                "sql": sql,
                "error": error,
                "seconds": round(time.monotonic() - started, 1),
                "llm_calls": usage.calls,
                "llm_seconds": round(usage.llm_seconds, 1),
                "input_tokens": usage.input_tokens,
                "context_tables": usage.context_tables,
            }
            out.write(json.dumps(record) + "\n")
            out.flush()
            print(f"{item['id']}: {record['seconds']}s", flush=True)


if __name__ == "__main__":
    main()
