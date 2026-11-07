# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Score recorded runs against the golden SQL and print a report without row data.

Every query runs in a read-only session::

    uv run python -m ontology_sql_agent.eval.report runs/agent.jsonl runs/classic.jsonl
    uv run python -m ontology_sql_agent.eval.report --check-golden
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import psycopg
import yaml
from dotenv import dotenv_values
from psycopg.rows import dict_row

from ontology_sql_agent.eval.run import GOLDEN
from ontology_sql_agent.eval.scoring import results_match, retrieval_recall


def _connect() -> psycopg.Connection:
    url = str(dotenv_values(".env")["CONNECTION_STRINGS"]).split(",")[0].strip()
    return psycopg.connect(
        url,
        autocommit=True,
        row_factory=dict_row,
        options="-c default_transaction_read_only=on -c statement_timeout=30000",
    )


def _rows(connection: psycopg.Connection, sql: str) -> list[dict[str, Any]]:
    return connection.execute(sql.encode()).fetchall()


def check_golden(questions: list[dict[str, Any]]) -> int:
    """Run every reference query, so a broken one fails before any arm is scored."""
    broken = 0
    with _connect() as connection:
        for item in questions:
            if not item.get("sql"):
                print(f"{item['id']}: unanswerable")
                continue
            try:
                print(f"{item['id']}: {len(_rows(connection, item['sql']))} row(s)")
            except psycopg.Error as error:
                broken += 1
                print(f"{item['id']}: BROKEN {str(error).splitlines()[0]}")
    print(f"{len(questions)} question(s), {broken} broken")
    return broken


def score_record(
    connection: psycopg.Connection,
    item: dict[str, Any],
    record: dict[str, Any],
    gold_rows: list[dict[str, Any]] | None,
) -> tuple[bool, float | None]:
    """Return ``(correct, retrieval recall)`` for one recorded answer."""
    if not item.get("sql"):
        if not record["sql"]:
            return True, None
        try:
            return not _rows(connection, record["sql"]), None
        except psycopg.Error:
            return True, None
    recall = retrieval_recall(item["sql"], record["context_tables"])
    if not record["sql"]:
        return False, recall
    try:
        return results_match(gold_rows or [], _rows(connection, record["sql"])), recall
    except psycopg.Error:
        return False, recall


def outcome_cell(correct: bool | None) -> str:
    """A question an arm never answered is not the same as a wrong answer."""
    if correct is None:
        return "-"
    return "ok" if correct else "WRONG"


def report(questions: list[dict[str, Any]], paths: list[Path]) -> None:
    by_id = {item["id"]: item for item in questions}
    outcomes: dict[str, dict[str, bool]] = defaultdict(dict)
    with _connect() as connection:
        gold_rows = {
            item["id"]: _rows(connection, item["sql"])
            for item in questions
            if item.get("sql")
        }
        print(
            "| Arm | Correct | Recall | Median s | Max s | LLM s | LLM calls | Tokens |"
        )
        print("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for path in paths:
            records = [json.loads(line) for line in path.read_text().splitlines()]
            correct, recalls = 0, []
            for record in records:
                ok, recall = score_record(
                    connection,
                    by_id[record["id"]],
                    record,
                    gold_rows.get(record["id"]),
                )
                outcomes[record["id"]][record["arm"]] = ok
                correct += ok
                if recall is not None:
                    recalls.append(recall)
            seconds = [r["seconds"] for r in records]
            calls = [r["llm_calls"] for r in records if r["llm_calls"] is not None]
            llm_seconds = [r["llm_seconds"] for r in records if r.get("llm_seconds")]
            tokens = [r["input_tokens"] for r in records if r["input_tokens"]]
            print(
                f"| {records[0]['arm']} | {correct}/{len(records)} "
                f"| {statistics.mean(recalls):.0%} "
                f"| {statistics.median(seconds):.0f} | {max(seconds):.0f} "
                f"| {f'{statistics.median(llm_seconds):.0f}' if llm_seconds else '-'} "
                f"| {statistics.median(calls) if calls else '-'} "
                f"| {statistics.median(tokens) if tokens else '-'} |"
            )
    arms = sorted({arm for result in outcomes.values() for arm in result})
    print("\n| Question | " + " | ".join(arms) + " |")
    print("| --- |" + " --- |" * len(arms))
    for question_id, result in outcomes.items():
        cells = [outcome_cell(result.get(arm)) for arm in arms]
        print(f"| {question_id} | " + " | ".join(cells) + " |")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path, nargs="*")
    parser.add_argument("--golden", type=Path, default=GOLDEN)
    parser.add_argument("--check-golden", action="store_true")
    args = parser.parse_args()
    questions = yaml.safe_load(args.golden.read_text())["questions"]
    if args.check_golden:
        raise SystemExit(1 if check_golden(questions) else 0)
    report(questions, args.runs)


if __name__ == "__main__":
    main()
