# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Loop perbaikan: umpan balik untuk generator, atau jawaban gagal untuk pemanggil."""

from typing import Any

from sql_agent.core.logging import get_logger
from sql_agent.modules.repair.policy import MAX_RETRIES, failure_answer, repair_feedback
from sql_agent.schemas import State

logger = get_logger(__name__)


def sql_repair(state: State) -> dict[str, Any]:
    logger.info(f"SQL Repair (attempt {state.retry_count + 1}/{MAX_RETRIES})")
    return {
        "retry_count": state.retry_count + 1,
        "retry_feedback": repair_feedback(state),
        "last_error": state.error,
    }


def sql_failure(state: State) -> dict[str, Any]:
    return {"answer": failure_answer(state)}
