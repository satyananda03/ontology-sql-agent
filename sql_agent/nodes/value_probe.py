# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Literal

from sql_agent.core.logging import get_logger
from sql_agent.modules.repair.value_probe import probe_feedback, probe_lines
from sql_agent.schemas import State

logger = get_logger(__name__)


def value_probe(state: State) -> dict[str, Any]:
    logger.info("Value Probe")
    sql = state.raw_sql_query or state.sql_query or ""
    tables = state.ontology.get("path_state", {}).get("relevant_tables") or []
    try:
        lines = probe_lines(sql, tables, state.connector)
    except Exception:  # noqa: BLE001 — a failed probe must not end the run
        logger.exception("[VALUE-PROBE] gagal, lanjut tanpa koreksi")
        lines = []

    logger.info(f"[VALUE-PROBE] {len(lines)} kolom diperiksa")
    if not lines:
        return {"retry_feedback": None}
    return {
        "value_probed": True,
        "retry_feedback": probe_feedback(sql, lines),
        "retry_count": state.retry_count + 1,
    }


def check_value_probe(state: State) -> Literal["retry", "done"]:
    return "retry" if state.retry_feedback else "done"
