# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from typing import Any

from sql_agent.core.config import settings
from sql_agent.core.logging import get_logger
from sql_agent.modules.answer.formatting import (
    format_query_results_for_llm,
    new_filter_words_note,
)
from sql_agent.modules.sql.filters import new_filter_words
from sql_agent.schemas import State

logger = get_logger(__name__)


def sql_result_analyzer(state: State) -> dict[str, Any]:
    logger.info("SQL Result Analyser")
    formatted_results = format_query_results_for_llm(
        state.sql_execution_result or {},
        sql=state.sql_query,
        retried=state.value_probed,
        max_rows=settings.sql_agent_max_rows,
    )
    rows = (state.sql_execution_result or {}).get("data")
    if state.value_probed and rows:
        words = new_filter_words(
            state.raw_sql_query or state.sql_query or "", state.user_query
        )
        if words:
            logger.info(
                f"[RESULT] filter retry memakai kata di luar pertanyaan: {words}"
            )
            formatted_results = new_filter_words_note(words) + formatted_results
    return {"answer": formatted_results}
