# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
import re
from typing import Any, Literal

import sqlglot
from sqlglot import exp

from auto_ontology.utils.sql_identifiers import quoted_identifier
from sql_agent.state import State

logger = logging.getLogger(__name__)

MAX_PROBES = 5
PROBE_LIMIT = 15
PROBE_VALUE_CHARS = 100
PROBE_TIMEOUT_S = 10.0
_TEXT_PREDICATES = (exp.EQ, exp.NEQ, exp.Like, exp.ILike, exp.In)


def extract_text_filters(sql: str) -> list[tuple[str, str]]:
    try:
        tree = sqlglot.parse_one(sql, dialect="postgres")
    except sqlglot.errors.SqlglotError:
        logger.warning("[VALUE-PROBE] SQL tidak bisa di-parse, probe dilewati")
        return []
    seen: dict[tuple[str, str], None] = {}
    for pred in tree.find_all(*_TEXT_PREDICATES):
        if pred.find(exp.Select):
            continue
        col = pred.find(exp.Column)
        lit = next((lit for lit in pred.find_all(exp.Literal) if lit.is_string), None)
        if col and lit and (value := lit.this.strip("%").strip()):
            seen[(col.name, value)] = None
    return list(seen)


def _clip(value: str) -> str:
    return value if len(value) <= PROBE_VALUE_CHARS else value[:PROBE_VALUE_CHARS] + "…"


def _probe_targets(state: State) -> list[tuple[dict[str, Any], str, str]]:
    """``(table, column, literal)`` for each text filter on a table the SQL reads."""
    sql = state.raw_sql_query or state.sql_query or ""
    tables = state.ontology.get("path_state", {}).get("relevant_tables") or []
    targets = []
    for col, literal in extract_text_filters(sql):
        for table in tables:
            if re.search(rf"\b{re.escape(table['name'])}\b", sql) and any(
                c.get("name") == col for c in table.get("columns") or []
            ):
                targets.append((table, col, literal))
    return targets[:MAX_PROBES]


def _closest_values(
    connector: Any, table: dict[str, Any], col: str, literal: str
) -> list[str]:
    column = quoted_identifier(col, "postgres")
    relation = connector.qualify(table.get("schema_name"), table["name"])
    frame = connector.execute(
        f"SELECT DISTINCT {column}::text AS v, word_similarity(%s, {column}::text) AS s "
        f"FROM {relation} WHERE {column} IS NOT NULL "
        f"ORDER BY s DESC, v LIMIT {PROBE_LIMIT}",
        [literal],
        timeout_s=PROBE_TIMEOUT_S,
    )
    return frame["v"].tolist() if len(frame) else []


def value_probe(state: State) -> dict[str, Any]:
    logger.info("Value Probe")
    lines = []
    try:
        for table, col, literal in _probe_targets(state):
            values = ", ".join(
                f"'{_clip(v)}'"
                for v in _closest_values(state.connector, table, col, literal)
            )
            lines.append(
                f'- "{table.get("schema_name")}"."{table["name"]}"."{col}" '
                f"(dicari: '{literal}'): {values or '(kolom kosong)'}"
            )
    except Exception:  # noqa: BLE001 — a failed probe must not end the run
        logger.exception("[VALUE-PROBE] gagal, lanjut tanpa koreksi")
        lines = []

    logger.info(f"[VALUE-PROBE] {len(lines)} kolom diperiksa")
    if not lines:
        return {"retry_feedback": None}
    feedback = (
        "<previous_attempt>\n"
        "Query sebelumnya dieksekusi tapi tidak menemukan data (0 baris atau hasil hitungan 0) :\n"
        f"{state.raw_sql_query or state.sql_query}\n\n"
        "Nilai yang benar-benar ada di database untuk kolom yang difilter (urut dari yang paling mirip dengan nilai yang dicari) :\n"
        + "\n".join(lines)
        + "\n\nTulis ulang query memakai nilai persis dari daftar di atas bila ada yang sesuai maksud pertanyaan."
        "Nilai berakhiran '…' adalah cuplikan teks panjang: filter kolom itu dengan ILIKE kata kunci khas, bukan =."
        "Jika tidak ada yang sesuai, pertahankan filternya — hasil kosong berarti datanya memang tidak ada.\n"
        "</previous_attempt>"
    )
    return {
        "value_probed": True,
        "retry_feedback": feedback,
        "retry_count": state.retry_count + 1,
    }


def check_value_probe(state: State) -> Literal["retry", "done"]:
    return "retry" if state.retry_feedback else "done"
