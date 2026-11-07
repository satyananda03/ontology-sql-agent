# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from typing import Any, Literal

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

from ontology_sql_agent.state import State

logger = logging.getLogger(__name__)

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


def sql_safety_validator(state: State) -> dict[str, Any]:
    """Validate if the SQL query is safe.

    Checks the parsed statement rather than searching the text for keywords, so
    a value such as ``ILIKE '%update%'`` is not mistaken for a write.
    """
    logger.info("SQL Safety Validator")
    problem = read_only_problem(state.sql_query or "", "postgres")
    if problem:
        logger.error(f"SQL is not a read-only query: {problem}")
        return {"error": problem, "sql_safety_status": "unsafe"}
    return {"sql_safety_status": "safe"}


def check_sql_safety(state: State) -> Literal["safe", "unsafe"]:
    """Check if the SQL query is safe."""
    return "safe" if state.sql_safety_status == "safe" else "unsafe"
