# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Pilih tabel dan susun konteks skema dari ontologi, menggantikan schema navigator.

Navigator lama mengirim katalog seluruh tabel ke LLM. Di sini agent retrieval
auto_ontology yang memilih (``modules/retrieval/pipeline.py``), lalu hasilnya
dipetakan ke state (``modules/retrieval/context.py``). Pertanyaan yang sama
dalam ``cache.TTL_S`` memakai hasil retrieval sebelumnya (``modules/retrieval/cache.py``).
"""

from typing import Any, Literal

from sql_agent.core.logging import get_logger
from sql_agent.modules.retrieval import cache, pipeline
from sql_agent.modules.retrieval.context import context_update, renavigation_question
from sql_agent.schemas import State

logger = get_logger(__name__)


def ontology_context(state: State) -> dict[str, Any]:
    logger.info("Ontology Context - retrieving relevant tables")
    ontology = cache.get(state.user_query)
    if ontology is None:
        ontology = pipeline.retrieve(state.user_query)
    update = context_update(ontology)
    if update["selected_table"]:
        cache.put(state.user_query, ontology)
    logger.info(f"Selected tables: {update['selected_table']}")
    return update


def check_schema_navigation(state: State) -> Literal["success", "failure"]:
    return "success" if state.selected_table else "failure"


def schema_renavigator(state: State) -> dict[str, Any]:
    previous = state.selected_table
    count = state.renavigation_count + 1
    logger.info(f"Schema Re-navigator ({count}) - tabel sebelumnya: {previous}")
    question = renavigation_question(state.user_query, previous, state.error)
    update = context_update(pipeline.retrieve(question))
    update["renavigation_count"] = count
    if update["selected_table"]:
        # Next time the same question goes straight to the tables that answered it.
        cache.put(state.user_query, update["ontology"])
        update.update(retry_feedback=None, last_error=None)
    return update


def check_renavigation(state: State) -> Literal["success", "failure"]:
    return "failure" if state.error else "success"
