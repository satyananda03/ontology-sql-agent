# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Literal

from ontology_sql_agent.db import run_query
from ontology_sql_agent.nodes.repair import MAX_RETRIES, retry_transient, route_failure
from ontology_sql_agent.nodes.value_probe import extract_text_filters
from ontology_sql_agent.state import State

logger = logging.getLogger(__name__)


def sql_executor(state: State) -> dict[str, Any]:
    logger.info("SQL Executor")
    result = retry_transient(lambda: run_query(state.sql_query or "", state.connector))
    if result["success"]:
        sample = result["data"][:50] if result["data"] else None
        logger.debug(f"SQL execution status: success | sample={sample}...")
        return {"sql_execution_status": "success", "sql_execution_result": result}
    # Dipotong biar tidak membanjiri konteks LLM.
    return {
        "sql_execution_status": "failure",
        "sql_execution_result": result,
        "error": str(result["error"])[:500],
        "error_code": result["error_code"],
    }


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


def check_sql_execution(
    state: State,
) -> Literal["success", "empty", "repair", "renavigate", "fail"]:
    logger.debug(f"→ Routing to {state.sql_execution_status}")
    if state.sql_execution_status != "success":
        return route_failure(state)
    rows = (state.sql_execution_result or {}).get("data") or []
    looks_empty = not rows or (
        _is_zero_aggregate(rows)
        and bool(extract_text_filters(state.raw_sql_query or state.sql_query or ""))
    )
    if looks_empty and not state.value_probed and state.retry_count < MAX_RETRIES:
        return "empty"
    return "success"
