# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Decide whether a predicted query returned the reference answer."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any

import sqlglot
from sqlglot import exp


def _value_key(value: Any) -> str:
    """Compare values by meaning: 3, 3.0 and Decimal('3.00') are the same number."""
    if value is None:
        return ""
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        return f"{round(float(value), 2):g}"
    return " ".join(str(value).split()).casefold()


def _column_key(rows: list[dict[str, Any]], column: str) -> Counter:
    return Counter(_value_key(row.get(column)) for row in rows)


def results_match(gold: list[dict[str, Any]], predicted: list[dict[str, Any]]) -> bool:
    """Whether *predicted* holds the same rows, ignoring order and extra columns.

    Every reference column must appear in the prediction with the same values,
    whatever its name. An agent adding a helpful column is still correct; a wrong
    or missing row, including a duplicate from a bad join, is not.
    """
    if len(gold) != len(predicted):
        return False
    if not gold:
        return True
    predicted_columns = [_column_key(predicted, c) for c in predicted[0]]
    return all(_column_key(gold, c) in predicted_columns for c in gold[0])


def tables_in_sql(sql: str) -> set[str]:
    """The table names a query reads, without CTE names."""
    tree = sqlglot.parse_one(sql, read="postgres")
    cte_names = {cte.alias for cte in tree.find_all(exp.CTE)}
    return {t.name for t in tree.find_all(exp.Table)} - cte_names


def retrieval_recall(gold_sql: str, context_tables: list[str]) -> float:
    """Share of the reference query's tables that reached SQL generation."""
    needed = tables_in_sql(gold_sql)
    if not needed:
        return 1.0
    return len(needed & set(context_tables)) / len(needed)
