# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Literal

from sql_agent.core.logging import get_logger
from sql_agent.modules.sql.safety import read_only_problem
from sql_agent.schemas import State

logger = get_logger(__name__)


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
