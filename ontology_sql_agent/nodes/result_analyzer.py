# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
import re
from typing import Any

import sqlglot
from sqlglot import exp

from ontology_sql_agent.state import State
from ontology_sql_agent.utils import format_query_results_for_llm, max_rows

logger = logging.getLogger(__name__)


def new_filter_words(sql: str, question: str) -> list[str]:
    try:
        tree = sqlglot.parse_one(sql, dialect="postgres")
    except sqlglot.errors.SqlglotError:
        return []
    asked = re.findall(r"\w+", question.lower())
    found: dict[str, None] = {}
    for pred in tree.find_all(exp.ILike, exp.Like):
        lit = pred.expression
        if not (isinstance(lit, exp.Literal) and lit.is_string):
            continue
        for word in re.findall(r"\w+", lit.this):
            if not any(word.lower() in a for a in asked):
                found[word] = None
    return list(found)


def sql_result_analyzer(state: State) -> dict[str, Any]:
    logger.info("SQL Result Analyser")
    formatted_results = format_query_results_for_llm(
        state.sql_execution_result or {},
        sql=state.sql_query,
        retried=state.value_probed,
        max_rows=max_rows(),
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
            formatted_results = (
                "CATATAN : tidak ada yang cocok persis dengan pertanyaan. Filter memakai "
                f"kata yang tidak ada di pertanyaan: {', '.join(repr(w) for w in words)}. "
                "Baris di bawah adalah nilai yang mirip, belum tentu yang ditanyakan.\n"
                + formatted_results
            )
    return {"answer": formatted_results}
