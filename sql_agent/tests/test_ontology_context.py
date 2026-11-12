# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from typing import Any

import pytest

from sql_agent.nodes import ontology_context as module
from sql_agent.nodes.repair import INFO_NOT_FOUND
from sql_agent.state import State

TABLE = {
    "name": "fact_partisipasi_program",
    "schema_name": "iccn_dwh",
    "database_name": "db",
    "id": "t1",
    "columns": [{"name": "nama_pendaftar", "data_type": "text"}],
}


class FakeConnector:
    database_name = "db"
    dialect = "postgres"


def _ontology(tables: list[dict], **path_state: Any) -> dict[str, Any]:
    return {
        "connectors": [FakeConnector()],
        "glossary": [],
        "path_state": {"relevant_tables": tables, "target_db": "db", **path_state},
    }


def test_tables_become_the_classic_schema_context() -> None:
    update = module.context_update(_ontology([TABLE]))
    assert update["selected_table"] == ["fact_partisipasi_program"]
    assert "fact_partisipasi_program" in update["schema_context"]
    assert "nama_pendaftar" in update["schema_context"]
    assert update["error"] is None


def test_no_tables_is_information_not_found() -> None:
    update = module.context_update(_ontology([]))
    assert update["selected_table"] == []
    assert update["error_code"] == INFO_NOT_FOUND


def test_knowledge_carries_definitions_synonyms_and_glossary() -> None:
    ontology = _ontology(
        [TABLE],
        sql_attributes_str=["Researcher: jenis_program = 'RISET'"],
        term_synonyms={"Program Participation": ["pendaftar", "peserta"]},
    )
    ontology["glossary"] = [{"name": "korda", "description": "koordinator daerah"}]
    knowledge = module.context_update(ontology)["knowledge_context"]
    assert "Researcher: jenis_program = 'RISET'" in knowledge
    assert "Program Participation: pendaftar, peserta" in knowledge
    assert "korda: koordinator daerah" in knowledge


def test_matched_custom_analyses_reach_the_generator_as_few_shot_examples() -> None:
    example = "name: Researcher per bidang, sql: SELECT bidang, COUNT(*) FROM riset"
    ontology = _ontology([TABLE], custom_analyses_str=[example])
    knowledge = module.context_update(ontology)["knowledge_context"]
    assert "FEW-SHOT EXAMPLES" in knowledge
    assert f"- {example}" in knowledge


def test_join_paths_reach_the_generator() -> None:
    hop = {
        "source_schema": "iccn_dwh",
        "source_table": "detail_program_riset",
        "source_column": "partisipasi_id",
        "target_schema": "iccn_dwh",
        "target_table": "fact_partisipasi_program",
        "target_column": "partisipasi_id",
    }
    ontology = _ontology(
        [TABLE],
        primary_attribute={"table_name": "detail_program_riset", "col_name": "x"},
        attribute_join_paths=[{"path": [hop]}],
    )
    knowledge = module.context_update(ontology)["knowledge_context"]
    assert "JOIN PATHS" in knowledge
    assert "detail_program_riset" in knowledge and "partisipasi_id" in knowledge


def test_nothing_to_add_leaves_knowledge_empty() -> None:
    assert module.context_update(_ontology([TABLE]))["knowledge_context"] == ""


def test_renavigation_asks_again_with_what_was_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked: list[str] = []

    def retrieve(question: str) -> dict[str, Any]:
        asked.append(question)
        return _ontology([TABLE])

    monkeypatch.setattr(module.retrieval, "retrieve", retrieve)
    state = State(
        user_query="siapa researcher",
        selected_table=["dim_user"],
        error="kolom tidak ada",
        retry_feedback="old",
    )
    update = module.schema_renavigator(state)
    assert "dim_user" in asked[0] and "kolom tidak ada" in asked[0]
    assert update["renavigation_count"] == 1
    assert update["retry_feedback"] is None and update["error"] is None
    assert module.check_renavigation(state.model_copy(update=update)) == "success"


def test_renavigation_that_finds_nothing_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module.retrieval, "retrieve", lambda question: _ontology([]))
    update = module.schema_renavigator(State(user_query="q", error="x"))
    assert module.check_renavigation(State(user_query="q", **update)) == "failure"
