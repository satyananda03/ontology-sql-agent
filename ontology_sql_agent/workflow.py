# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from ontology_sql_agent.nodes.ontology_context import (
    check_renavigation,
    check_schema_navigation,
    ontology_context,
    schema_renavigator,
)
from ontology_sql_agent.nodes.repair import sql_failure, sql_repair
from ontology_sql_agent.nodes.result_analyzer import sql_result_analyzer
from ontology_sql_agent.nodes.safety_validator import (
    check_sql_safety,
    sql_safety_validator,
)
from ontology_sql_agent.nodes.semantic_search import semantic_search
from ontology_sql_agent.nodes.sql_executor import check_sql_execution, sql_executor
from ontology_sql_agent.nodes.sql_generator import check_sql_generation, sql_generator
from ontology_sql_agent.nodes.syntax_validator import (
    check_sql_syntax,
    sql_syntax_validator,
)
from ontology_sql_agent.nodes.value_probe import check_value_probe, value_probe
from ontology_sql_agent.state import State


def create_workflow() -> StateGraph:
    workflow = StateGraph(State)
    workflow.add_node("ontology_context", ontology_context)
    workflow.add_node("semantic_search", semantic_search)
    workflow.add_node("sql_generator", sql_generator)
    workflow.add_node("sql_safety_validator", sql_safety_validator)
    workflow.add_node("sql_syntax_validator", sql_syntax_validator)
    workflow.add_node("sql_executor", sql_executor)
    workflow.add_node("sql_result_analyzer", sql_result_analyzer)
    workflow.add_node("value_probe", value_probe)
    workflow.add_node("sql_repair", sql_repair)
    workflow.add_node("sql_failure", sql_failure)
    workflow.add_node("schema_renavigator", schema_renavigator)

    workflow.add_edge(START, "ontology_context")
    workflow.add_conditional_edges(
        "ontology_context",
        check_schema_navigation,
        {"success": "semantic_search", "failure": "sql_failure"},
    )
    # Topik di pertanyaan -> ID baris yang cocok untuk generator; no-op bila
    # tabel terpilih tidak punya kolom *_vector.
    workflow.add_edge("semantic_search", "sql_generator")

    # Pilihan tabel terbukti kurang (generator tak bisa menulis SQL, atau
    # tabel/kolom tak ada di konteks) -> ambil ulang konteks dari ontologi,
    # dibatasi SQL_AGENT_MAX_RENAVIGATIONS.
    workflow.add_conditional_edges(
        "sql_generator",
        check_sql_generation,
        {
            "success": "sql_safety_validator",
            "renavigate": "schema_renavigator",
            "fail": "sql_failure",
        },
    )
    workflow.add_conditional_edges(
        "schema_renavigator",
        check_renavigation,
        {"success": "semantic_search", "failure": "sql_failure"},
    )
    workflow.add_conditional_edges(
        "sql_safety_validator",
        check_sql_safety,
        {"safe": "sql_syntax_validator", "unsafe": END},
    )
    # Loop perbaikan (nodes/repair.py): error yang bisa diperbaiki dan hasil
    # kosong kembali ke sql_generator dengan satu jatah retry bersama.
    workflow.add_conditional_edges(
        "sql_syntax_validator",
        check_sql_syntax,
        {
            "valid": "sql_executor",
            "repair": "sql_repair",
            "renavigate": "schema_renavigator",
            "fail": "sql_failure",
        },
    )
    workflow.add_conditional_edges(
        "sql_executor",
        check_sql_execution,
        {
            "success": "sql_result_analyzer",
            "empty": "value_probe",
            "repair": "sql_repair",
            "renavigate": "schema_renavigator",
            "fail": "sql_failure",
        },
    )
    workflow.add_conditional_edges(
        "value_probe",
        check_value_probe,
        {"retry": "sql_generator", "done": "sql_result_analyzer"},
    )
    workflow.add_edge("sql_repair", "sql_generator")
    workflow.add_edge("sql_result_analyzer", END)
    workflow.add_edge("sql_failure", END)
    return workflow


@lru_cache(maxsize=1)
def get_workflow() -> Any:
    """The compiled graph, built once on first use."""
    return create_workflow().compile()
