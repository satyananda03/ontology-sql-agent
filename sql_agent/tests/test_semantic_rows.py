# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from typing import Any

import pandas as pd
import pytest

from sql_agent import semantic_rows as module
from sql_agent.semantic_rows import (
    SEMANTIC_TRUNCATED_NOTE,
    RelevantCandidates,
    SemanticFilter,
    SemanticPlan,
    SemanticRowsAgent,
    searchable_columns,
    sql_literal,
)

TABLE = {
    "name": "riset",
    "schema_name": "dwh",
    "database_name": "db",
    "pk": ["detail_id"],
    "columns": [
        {"name": "detail_id", "data_type": "integer"},
        {"name": "topik", "data_type": "text", "description": "Topik riset"},
        {"name": "topik_vector", "data_type": "vector"},
        {"name": "orphan_vector", "data_type": "vector"},
        {"name": "fake_vector", "data_type": "text"},
        {"name": "fake", "data_type": "text"},
    ],
}


class FakeConnector:
    database_name = "db"

    def __init__(self, ids: list[Any]) -> None:
        self.frame = pd.DataFrame(
            [{"id": i, "snippet": f"text {i}"} for i in ids], columns=["id", "snippet"]
        )
        self.calls: list[tuple] = []

    def qualify(self, schema: str, table: str) -> str:
        return f'"{schema}"."{table}"'

    def execute(self, sql: str, parameters: list, timeout_s: float) -> pd.DataFrame:
        self.calls.append((sql, parameters))
        return self.frame


def _state(connector: FakeConnector, evidence: str = "") -> dict[str, Any]:
    return {
        "llm": object(),
        "evidence": evidence,
        "connectors": [connector],
        "initial_question": "siapa peneliti pariwisata",
        "path_state": {"relevant_tables": [TABLE]},
    }


def _stub(
    monkeypatch: pytest.MonkeyPatch,
    filters: list[SemanticFilter],
    verified: list[int],
) -> list[str]:
    llm_schemas: list[str] = []

    def invoke(llm: Any, messages: list, schema: type) -> Any:
        llm_schemas.append(schema.__name__)
        if schema is SemanticPlan:
            return SemanticPlan(filters=filters)
        return RelevantCandidates(reasoning="", numbers=verified)

    monkeypatch.setattr(module, "invoke_with_structured_output", invoke)
    monkeypatch.setattr(module, "get_embed_params", lambda: None)
    monkeypatch.setattr(
        module, "embed_texts", lambda texts, *_: [[0.1, 0.2] for _ in texts]
    )
    monkeypatch.setattr(
        module, "rerank_hits", lambda query, rows, **_: rows[: module.VERIFY_K]
    )
    monkeypatch.setattr(module, "get_rerank_kwargs", lambda: {})
    return llm_schemas


FILTER = SemanticFilter(table="riset", column="topik_vector", query="pariwisata")


def test_only_real_vector_columns_with_a_source_are_searchable() -> None:
    assert list(searchable_columns([TABLE])) == [("riset", "topik_vector")]


def test_composite_key_tables_are_not_searchable() -> None:
    assert not searchable_columns([{**TABLE, "pk": ["a", "b"]}])


def test_no_llm_call_without_searchable_columns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schemas = _stub(monkeypatch, [FILTER], [])
    state = _state(FakeConnector([]))
    state["path_state"]["relevant_tables"] = [
        {**TABLE, "columns": TABLE["columns"][:2]}
    ]
    assert "evidence" not in SemanticRowsAgent().execute(state)
    assert schemas == []


def test_matches_become_a_placeholder_and_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub(monkeypatch, [FILTER], [2, 1, 2, 99])
    connector = FakeConnector([7, 8, 9])
    result = SemanticRowsAgent().execute(_state(connector, evidence="rule"))
    assert result["path_state"]["semantic_ids"] == {"__SEMANTIC_1__": "8, 7"}
    assert result["evidence"].startswith("rule\n\n")
    assert '"riset"."detail_id" IN (__SEMANTIC_1__)' in result["evidence"]
    assert connector.calls[0][1][1] == module.RECALL_K
    assert '"topik_vector" <=> %s::vector' in connector.calls[0][0]


def test_invented_column_never_reaches_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    bad = SemanticFilter(table="riset", column='x"; DROP TABLE t; --', query="q")
    _stub(monkeypatch, [bad], [])
    connector = FakeConnector([1])
    result = SemanticRowsAgent().execute(_state(connector))
    assert connector.calls == []
    assert "evidence" not in result


def test_no_match_yields_an_empty_id_list(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub(monkeypatch, [FILTER], [])
    result = SemanticRowsAgent().execute(_state(FakeConnector([1])))
    assert result["path_state"]["semantic_ids"] == {"__SEMANTIC_1__": "NULL"}


def test_search_failure_falls_back_to_keywords(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub(monkeypatch, [FILTER], [])

    def fail(*_: Any) -> None:
        raise RuntimeError("embedding endpoint down")

    monkeypatch.setattr(module, "embed_texts", fail)
    result = SemanticRowsAgent().execute(_state(FakeConnector([1])))
    assert result["path_state"]["semantic_ids"] == {}
    assert 'filter "riset"."topik" with ILIKE' in result["evidence"]


def test_all_reviewed_matching_at_the_limit_is_flagged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "RECALL_K", 3)
    monkeypatch.setattr(module, "VERIFY_K", 2)
    _stub(monkeypatch, [FILTER], [1, 2])
    state = _state(FakeConnector([1, 2, 3]))
    SemanticRowsAgent().execute(state)
    assert SEMANTIC_TRUNCATED_NOTE in str(state["path_state"].get("thoughts_log"))


def test_partial_match_is_not_flagged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "RECALL_K", 3)
    monkeypatch.setattr(module, "VERIFY_K", 2)
    _stub(monkeypatch, [FILTER], [1])
    state = _state(FakeConnector([1, 2, 3]))
    SemanticRowsAgent().execute(state)
    assert not state["path_state"].get("thoughts_log")


@pytest.mark.parametrize(
    ("value", "expected"), [(5, "5"), ("a'b", "'a''b'"), ("uuid-1", "'uuid-1'")]
)
def test_sql_literal_quotes_text_only(value: Any, expected: str) -> None:
    assert sql_literal(value) == expected
