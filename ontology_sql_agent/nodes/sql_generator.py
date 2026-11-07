# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import sqlglot
import yaml
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from sqlglot import exp

from auto_ontology.utils.llm_invoke import (
    get_llm_client,
    invoke_with_structured_output,
)
from ontology_sql_agent.nodes.repair import INFO_NOT_FOUND, can_renavigate
from ontology_sql_agent.nodes.semantic_search import fill_semantic_ids
from ontology_sql_agent.state import State
from ontology_sql_agent.utils import strip_sql_fences

logger = logging.getLogger(__name__)

FILTER_COLUMN_CHARS = 200
# The model classic_sql_agent generated with, so the two stay comparable.
DEFAULT_GENERATOR_MODEL = "qwen.qwen3-coder-480b-a35b-v1:0"
# Up from 700, which could cut a multi-join query off mid-statement.
GENERATOR_MAX_TOKENS = 2000

_PROMPTS = yaml.safe_load(
    Path(__file__).parents[1].joinpath("prompts.yaml").read_text()
)
_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _PROMPTS["sql_generator"]["system_prompt"]),
        ("human", _PROMPTS["sql_generator"]["user_prompt"]),
    ]
)


class SQLGeneratorOutput(BaseModel):
    cannot_answer: bool = Field(
        default=False,
        description=(
            "true if the tables/columns in the schema context do not contain the "
            "information asked. Then leave sql_query empty — never write a "
            "placeholder query such as SELECT 0 or SELECT NULL."
        ),
    )
    reason: str = Field(
        default="",
        description="When cannot_answer is true: which information is missing from the schema.",
    )
    sql_query: str = Field(
        default="",
        description=(
            "The complete PostgreSQL query string (empty when cannot_answer is true). "
            "Use double quotes for schema, table, and column names, example : "
            '{"sql_query": "SELECT \\"id\\" FROM \\"data_iccn_user\\".\\"profiles\\";"}'
            "Always prefix tables with the exact schema name from the provided context"
        ),
    )


@lru_cache(maxsize=1)
def _llm() -> BaseChatModel:
    model = os.environ.get("SQL_AGENT_GENERATOR_MODEL") or DEFAULT_GENERATOR_MODEL
    return get_llm_client(model=model, max_tokens=GENERATOR_MAX_TOKENS)


def add_filter_columns(sql: str) -> str:
    """Sertakan kolom yang difilter ILIKE/LIKE ke SELECT."""
    try:
        tree = sqlglot.parse_one(sql, dialect="postgres")
    except sqlglot.errors.SqlglotError:
        return sql
    where = tree.args.get("where") if isinstance(tree, exp.Select) else None
    if where is None or tree.args.get("group") or tree.args.get("distinct"):
        return sql
    if any(p.find(exp.Star, exp.AggFunc, exp.Window) for p in tree.expressions):
        return sql
    have = {p.alias_or_name.lower() for p in tree.expressions}
    have |= {c.name.lower() for p in tree.expressions for c in p.find_all(exp.Column)}
    extra = []
    for pred in where.find_all(exp.ILike, exp.Like):
        col, lit = pred.this, pred.expression
        if not (
            isinstance(col, exp.Column)
            and isinstance(lit, exp.Literal)
            and lit.is_string
        ):
            continue
        if pred.find_ancestor(exp.Select) is not tree or col.name.lower() in have:
            continue
        have.add(col.name.lower())
        extra.append(
            exp.alias_(
                exp.func("LEFT", col.copy(), exp.Literal.number(FILTER_COLUMN_CHARS)),
                col.name,
                quoted=True,
            )
        )
    if not extra:
        return sql
    tree.set("expressions", extra + tree.expressions)
    return tree.sql(dialect="postgres")


def sql_generator(state: State) -> dict[str, Any]:
    logger.info("SQL Generator")
    messages = _PROMPT.format_messages(
        user_query=state.user_query,
        schema_context=state.schema_context,
        knowledge_context=state.knowledge_context,
        semantic_context=state.semantic_context,
        retry_feedback=state.retry_feedback or "",
    )
    logger.info(
        "[SQL-GEN] using standard prompt"
        + (" (retry with probed values)" if state.retry_feedback else "")
    )
    response = invoke_with_structured_output(_llm(), messages, SQLGeneratorOutput)
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
        "sql_syntax_status": None,
        "sql_execution_status": None,
        "sql_execution_result": None,
    }


def check_sql_generation(state: State) -> Literal["success", "renavigate", "fail"]:
    if state.sql_query and state.sql_query.strip():
        return "success"
    if state.error_code == INFO_NOT_FOUND and can_renavigate(state):
        return "renavigate"
    return "fail"
