# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from sql_agent.nodes.ontology_context import (
    check_renavigation,
    check_schema_navigation,
    ontology_context,
    schema_renavigator,
)
from sql_agent.nodes.repair import sql_failure, sql_repair
from sql_agent.nodes.result_analyzer import sql_result_analyzer
from sql_agent.nodes.safety_validator import (
    check_sql_safety,
    sql_safety_validator,
)
from sql_agent.nodes.semantic_search import semantic_search
from sql_agent.nodes.sql_executor import check_sql_execution, sql_executor
from sql_agent.nodes.sql_generator import check_sql_generation, sql_generator
from sql_agent.nodes.value_probe import check_value_probe, value_probe
from sql_agent.state import State
from sql_agent.utils import timed


def create_workflow() -> StateGraph:
    workflow = StateGraph(State)
    nodes = {
        "ontology_context": ontology_context,
        "semantic_search": semantic_search,
        "sql_generator": sql_generator,
        "sql_safety_validator": sql_safety_validator,
        "sql_executor": sql_executor,
        "sql_result_analyzer": sql_result_analyzer,
        "value_probe": value_probe,
        "sql_repair": sql_repair,
        "sql_failure": sql_failure,
        "schema_renavigator": schema_renavigator,
    }
    for name, node in nodes.items():
        workflow.add_node(name, timed(name, node))

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
        {"safe": "sql_executor", "unsafe": END},
    )
    # Loop perbaikan (nodes/repair.py): error yang bisa diperbaiki dan hasil
    # kosong kembali ke sql_generator dengan satu jatah retry bersama. Tidak ada
    # EXPLAIN terpisah: executor mengembalikan error dan SQLSTATE yang sama, jadi
    # validasi sintaks hanya menambah satu round-trip DB per percobaan.
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
