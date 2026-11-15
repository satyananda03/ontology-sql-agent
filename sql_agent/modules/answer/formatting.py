# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Merender hasil eksekusi jadi teks yang dibaca agent pemanggil."""

import json
from typing import Any


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


def new_filter_words_note(words: list[str]) -> str:
    """Peringatan bahwa filter retry memakai kata yang tidak ada di pertanyaan."""
    return (
        "CATATAN : tidak ada yang cocok persis dengan pertanyaan. Filter memakai "
        f"kata yang tidak ada di pertanyaan: {', '.join(repr(w) for w in words)}. "
        "Baris di bawah adalah nilai yang mirip, belum tentu yang ditanyakan.\n"
    )
