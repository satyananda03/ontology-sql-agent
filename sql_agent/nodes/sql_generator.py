# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from functools import lru_cache
from typing import Any, Literal

from sql_agent.core.config import settings
from sql_agent.core.logging import get_logger
from sql_agent.modules.repair.policy import INFO_NOT_FOUND, can_renavigate
from sql_agent.modules.sql.rewrite import (
    add_filter_columns,
    fill_semantic_ids,
    strip_sql_fences,
)
from sql_agent.schemas import SQLGeneratorOutput, State
from sql_agent.services.llm_service import (
    StructuredChain,
    ainvoke_parsed,
    get_llm,
    structured_chain,
)
from sql_agent.services.prompt_service import PROMPTS_FILE

logger = get_logger(__name__)

# Up from 700, which could cut a multi-join query off mid-statement.
GENERATOR_MAX_TOKENS = 2000


@lru_cache(maxsize=1)
def _chain() -> StructuredChain:
    llm = get_llm(
        settings.sql_agent_generator_model,
        max_tokens=GENERATOR_MAX_TOKENS,
        timeout=settings.sql_agent_llm_timeout_s,
    )
    return structured_chain(llm, PROMPTS_FILE, "sql_generator", SQLGeneratorOutput)


async def sql_generator(state: State) -> dict[str, Any]:
    logger.info("SQL Generator")
    variables = {
        "user_query": state.user_query,
        "schema_context": state.schema_context,
        "knowledge_context": state.knowledge_context,
        "semantic_context": (
            f"<semantic_context>\n{state.semantic_context}\n</semantic_context>"
            if state.semantic_context
            else ""
        ),
        "retry_feedback": state.retry_feedback or "",
    }
    logger.info(
        "[SQL-GEN] using standard prompt"
        + (" (retry with probed values)" if state.retry_feedback else "")
    )
    response = await ainvoke_parsed(_chain(), variables)
    if response is None:
        logger.error("LLM returned None — structured output parsing failed.")
        return {
            "sql_query": "",
            "raw_sql_query": "",
            "error": "LLM gagal menghasilkan SQL terstruktur.",
            "error_code": None,
        }
    raw_sql = strip_sql_fences(response.sql_query)
    if response.cannot_answer or not raw_sql:
        reason = response.reason.strip() or "tidak disebutkan"
        logger.info(f"[SQL-GEN] tidak bisa dijawab dari tabel terpilih: {reason}")
        return {
            "sql_query": "",
            "raw_sql_query": "",
            "error": f"Informasi tidak ditemukan di tabel {state.selected_table}: {reason}",
            "error_code": INFO_NOT_FOUND,
        }
    logger.debug(f"Generated SQL: {raw_sql}")
    return {
        "sql_query": add_filter_columns(fill_semantic_ids(raw_sql, state.semantic_ids)),
        "raw_sql_query": raw_sql,
        "error": None,
        "error_code": None,
        "sql_execution_status": None,
        "sql_execution_result": None,
    }


def check_sql_generation(state: State) -> Literal["success", "renavigate", "fail"]:
    if state.sql_query and state.sql_query.strip():
        return "success"
    if state.error_code == INFO_NOT_FOUND and can_renavigate(state):
        return "renavigate"
    return "fail"
