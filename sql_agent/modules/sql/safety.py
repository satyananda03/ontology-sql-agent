# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Pemeriksaan read-only atas SQL hasil LLM."""

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

_WRITE_NODES = (
    exp.Alter,
    exp.Command,
    exp.Create,
    exp.Delete,
    exp.Drop,
    exp.Insert,
    exp.Into,
    exp.Merge,
    exp.TruncateTable,
    exp.Update,
)


def read_only_problem(sql: str, dialect: str | None) -> str:
    """Return why *sql* is not a single read-only query, or ``""`` when it is.

    Works on the parsed statement, so a word such as ``update`` inside a string
    literal is not mistaken for a write. This catches agent mistakes; the
    database role remains what actually enforces read-only access.
    """
    try:
        statements = [s for s in sqlglot.parse(sql, read=dialect or None) if s]
    except SqlglotError as error:
        return f"The SQL could not be parsed: {error}"
    if len(statements) != 1:
        return "Exactly one SQL statement is allowed."
    statement = statements[0]
    if not isinstance(statement, exp.Query):
        return "Only SELECT queries are allowed."
    if statement.find(*_WRITE_NODES):
        return "Only read-only queries are allowed."
    return ""
