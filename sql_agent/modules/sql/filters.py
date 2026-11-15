# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Membaca filter teks dari SQL dan menilai apakah hasilnya terlihat kosong."""

import re
from decimal import Decimal
from typing import Any

import sqlglot
from sqlglot import exp

from sql_agent.core.logging import get_logger

logger = get_logger(__name__)

_TEXT_PREDICATES = (exp.EQ, exp.NEQ, exp.Like, exp.ILike, exp.In)


def extract_text_filters(sql: str) -> list[tuple[str, str]]:
    """``(kolom, literal)`` tiap filter teks di *sql*, tanpa wildcard ``%``."""
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


def new_filter_words(sql: str, question: str) -> list[str]:
    """Kata di filter LIKE/ILIKE yang tidak ada di pertanyaan."""
    try:
        tree = sqlglot.parse_one(sql, dialect="postgres")
    except sqlglot.errors.SqlglotError:
        return []
    asked = re.findall(r"\w+", question.lower())
    found: dict[str, None] = {}
    for pred in tree.find_all(exp.ILike, exp.Like):
        lit = pred.expression
        if not (isinstance(lit, exp.Literal) and lit.is_string):
            continue
        for word in re.findall(r"\w+", lit.this):
            if not any(word.lower() in a for a in asked):
                found[word] = None
    return list(found)


def _is_zero_aggregate(rows: list[dict[str, Any]]) -> bool:
    if len(rows) != 1:
        return False
    for value in rows[0].values():
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            return False
        if value != 0:
            return False
    return True


def looks_empty(rows: list[dict[str, Any]], sql: str) -> bool:
    """Tanpa baris, atau satu baris agregat bernilai nol dari query yang punya filter teks."""
    return not rows or (_is_zero_aggregate(rows) and bool(extract_text_filters(sql)))
