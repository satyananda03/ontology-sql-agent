# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Helper query untuk node-node SQL agent."""

import json
import os
import re
from typing import Any, Literal

_FENCE_RE = re.compile(
    r"```[ \t]*[A-Za-z0-9_+-]*[ \t]*\r?\n(?P<body>.*?)(?:\r?\n[ \t]*```|$)",
    re.DOTALL,
)

ErrorKind = Literal["fixable", "transient", "fatal"]


def strip_sql_fences(text: str | None) -> str:
    """Buang pembungkus markdown dari SQL hasil LLM"""
    if not text:
        return ""
    match = _FENCE_RE.search(text)
    cleaned = match.group("body") if match else text
    return cleaned.strip().strip("`").strip()


def classify_error(sqlstate: str | None) -> ErrorKind:
    """Tentukan apakah mengulang ada gunanya, dan dengan cara apa."""
    if (
        sqlstate is None
        or sqlstate.startswith(("08", "53", "57P"))
        or sqlstate in ("40001", "40P01")
    ):
        return "transient"
    if sqlstate == "42501":
        return "fatal"
    if sqlstate.startswith(("42", "22", "0A")) or sqlstate in ("21000", "57014"):
        return "fixable"
    return "fatal"


def _sql_block(sql: str | None) -> str:
    return f"SQL: {sql.strip()}\n" if sql else ""


def format_query_results_for_llm(
    execution_result: dict[str, Any],
    sql: str | None = None,
    retried: bool = False,
    max_rows: int | None = None,
) -> str:
    """Render hasil eksekusi jadi blok teks untuk agent pemanggil."""
    sql = sql or execution_result.get("query_executed")
    if not execution_result.get("success"):
        return (
            "STATUS: error\n"
            f"{_sql_block(sql)}"
            f"ERROR: {execution_result.get('error')}\n"
            "Query gagal dieksekusi. Perjelas maksud pertanyaan lalu panggil tool ini lagi."
        )
    rows = execution_result.get("data") or []
    if not rows:
        if retried:
            return (
                "STATUS: empty\n"
                f"{_sql_block(sql)}"
                "Tidak ada baris yang cocok. Nilai filter teks sudah dicocokkan "
                "dengan isi database dan query sudah diulang, jadi datanya memang "
                "tidak tersedia."
            )
        return (
            "STATUS: empty\n"
            f"{_sql_block(sql)}"
            "Tidak ada baris yang cocok. Boleh dicoba sekali lagi dengan istilah atau "
            "ejaan lain; kalau tetap kosong, laporkan datanya tidak tersedia."
        )

    shown = rows if max_rows is None else rows[:max_rows]
    note = (
        f"CATATAN : hanya {len(shown)} dari {len(rows)} baris yang ditampilkan.\n"
        if len(shown) < len(rows)
        else ""
    )
    return (
        f"{note}ROWS : {len(rows)}\n"
        f"COLUMNS : {', '.join(rows[0].keys())}\n"
        "RESULT (JSONL) :\n"
        + "\n".join(json.dumps(r, ensure_ascii=False, default=str) for r in shown)
    )


def max_rows() -> int:
    """Rows handed to the calling agent; the rest are counted, not shown."""
    return int(os.environ.get("SQL_AGENT_MAX_ROWS") or 200)
