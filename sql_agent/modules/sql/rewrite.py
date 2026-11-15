# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Penulisan ulang SQL hasil LLM oleh kode, sebelum dieksekusi."""

import re

import sqlglot
from sqlglot import exp

from sql_agent.core.logging import get_logger

logger = get_logger(__name__)

FILTER_COLUMN_CHARS = 200

_FENCE_RE = re.compile(
    r"```[ \t]*[A-Za-z0-9_+-]*[ \t]*\r?\n(?P<body>.*?)(?:\r?\n[ \t]*```|$)",
    re.DOTALL,
)


def strip_sql_fences(text: str | None) -> str:
    """Buang pembungkus markdown dari SQL hasil LLM"""
    if not text:
        return ""
    match = _FENCE_RE.search(text)
    cleaned = match.group("body") if match else text
    return cleaned.strip().strip("`").strip()


def fill_semantic_ids(sql: str, ids_by_placeholder: dict[str, str]) -> str:
    """Ganti placeholder ``__SEMANTIC_n__`` dengan daftar ID dari semantic_search."""
    for placeholder, ids in ids_by_placeholder.items():
        if placeholder not in sql:
            logger.warning(f"[SEMANTIC] generator tidak memakai {placeholder}")
        sql = sql.replace(placeholder, ids)
    return sql


def add_filter_columns(sql: str) -> str:
    """Sertakan kolom yang difilter ILIKE/LIKE ke SELECT."""
    try:
        tree = sqlglot.parse_one(sql, dialect="postgres")
    except sqlglot.errors.SqlglotError:
        return sql
    where = tree.args.get("where") if isinstance(tree, exp.Select) else None
    if where is None or tree.args.get("group") or tree.args.get("distinct"):
        return sql
    if any(p.find(exp.Star, exp.AggFunc, exp.Window) for p in tree.expressions):
        return sql
    have = {p.alias_or_name.lower() for p in tree.expressions}
    have |= {c.name.lower() for p in tree.expressions for c in p.find_all(exp.Column)}
    extra = []
    for pred in where.find_all(exp.ILike, exp.Like):
        col, lit = pred.this, pred.expression
        if not (
            isinstance(col, exp.Column)
            and isinstance(lit, exp.Literal)
            and lit.is_string
        ):
            continue
        if pred.find_ancestor(exp.Select) is not tree or col.name.lower() in have:
            continue
        have.add(col.name.lower())
        extra.append(
            exp.alias_(
                exp.func("LEFT", col.copy(), exp.Literal.number(FILTER_COLUMN_CHARS)),
                col.name,
                quoted=True,
            )
        )
    if not extra:
        return sql
    tree.set("expressions", extra + tree.expressions)
    return tree.sql(dialect="postgres")
