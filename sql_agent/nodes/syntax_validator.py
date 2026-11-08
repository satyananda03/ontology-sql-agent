# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from typing import Any, Literal

from sql_agent.db import explain
from sql_agent.nodes.repair import retry_transient, route_failure
from sql_agent.state import State

logger = logging.getLogger(__name__)


def sql_syntax_validator(state: State) -> dict[str, Any]:
    logger.info("SQL Syntax Validator")
    result = retry_transient(lambda: explain(state.sql_query or "", state.connector))
    if result["valid_syntax"]:
        return {"sql_syntax_status": "valid"}
    logger.warning(f"[SYNTAX] invalid [{result['error_code']}]: {result['error']}")
    return {
        "sql_syntax_status": "invalid",
        "error": result["error"][:500],
        "error_code": result["error_code"],
    }


def check_sql_syntax(state: State) -> Literal["valid", "repair", "renavigate", "fail"]:
    if state.sql_syntax_status == "valid":
        return "valid"
    return route_failure(state)
