# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

import asyncio
from typing import Any

import pandas as pd
import pytest

from sql_agent.modules.semantic import bm25_search
from sql_agent.modules.semantic import rows as module
from sql_agent.modules.semantic.rows import (
    SEMANTIC_TRUNCATED_NOTE,
    rrf,
    searchable_columns,
    sql_literal,
)
from sql_agent.schemas import RelevantCandidates, SemanticFilter, SemanticPlan

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


def _frame(ids: list[Any]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"id": i, "snippet": f"text {i}"} for i in ids], columns=["id", "snippet"]
    )


class FakeConnector:
    """Answers by query kind, since the two arms run in parallel in any order.

    ``bm25_ids=None`` means the table has no ``topik_bm25`` column.
    """

    database_name = "db"

    def __init__(self, ids: list[Any], bm25_ids: list[Any] | None = None) -> None:
        self.vector, self.bm25 = _frame(ids), bm25_ids
        self.calls: list[tuple] = []

    def qualify(self, schema: str, table: str) -> str:
        return f'"{schema}"."{table}"'

    def execute(self, sql: str, parameters: list, timeout_s: float) -> pd.DataFrame:
        self.calls.append((sql, parameters))
        if "information_schema" in sql:
            return pd.DataFrame([{"x": 1}] if self.bm25 is not None else [])
        if "|||" in sql:
            return _frame(self.bm25 or [])
        return self.vector

    def call(self, marker: str) -> tuple:
        return next(c for c in self.calls if marker in c[0])


@pytest.fixture(autouse=True)
def no_known_bm25_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bm25_search, "_columns", {})


def _run(state: dict[str, Any]) -> dict[str, Any]:
    return asyncio.run(module.semantic_rows(state))


class FakeEmbeddings:
    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]


def _state(connector: FakeConnector) -> dict[str, Any]:
    return {
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

    # The chain stands in as its schema, which is all the fake LLM needs.
    async def invoke(schema: type, variables: dict) -> Any:
        llm_schemas.append(schema.__name__)
        if schema is SemanticPlan:
            return SemanticPlan(filters=filters)
        return RelevantCandidates(reasoning="", numbers=verified)

    # The reranker keeps the vector order, best first.
    async def rerank(query: str, documents: list[str], top_n: int) -> list[dict]:
        return [
            {"index": i, "relevance_score": float(-i)} for i in range(len(documents))
        ][:top_n]

    monkeypatch.setattr(module, "_chain", lambda prompt_name, schema: schema)
    monkeypatch.setattr(module, "ainvoke_parsed", invoke)
    monkeypatch.setattr(module, "get_embeddings", lambda **_: FakeEmbeddings())
    monkeypatch.setattr(module, "get_reranker", lambda **_: rerank)
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
    assert "semantic_instructions" not in _run(state)
    assert schemas == []


def test_matches_become_a_placeholder_and_instructions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub(monkeypatch, [FILTER], [2, 1, 2, 99])
    connector = FakeConnector([7, 8, 9])
    result = _run(_state(connector))
    assert result["path_state"]["semantic_ids"] == {"__SEMANTIC_1__": "8, 7"}
    assert '"riset"."detail_id" IN (__SEMANTIC_1__)' in result["semantic_instructions"]
    vector_sql, parameters = connector.call("<=>")
    assert '"topik_vector" <=> %s::vector' in vector_sql
    assert parameters[1] == module.RECALL_K
    assert not any("|||" in sql for sql, _ in connector.calls)


def test_invented_column_never_reaches_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    bad = SemanticFilter(table="riset", column='x"; DROP TABLE t; --', query="q")
    _stub(monkeypatch, [bad], [])
    connector = FakeConnector([1])
    result = _run(_state(connector))
    assert connector.calls == []
    assert "semantic_instructions" not in result


def test_no_match_yields_an_empty_id_list(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub(monkeypatch, [FILTER], [])
    result = _run(_state(FakeConnector([1])))
    assert result["path_state"]["semantic_ids"] == {"__SEMANTIC_1__": "NULL"}


def test_search_failure_falls_back_to_keywords(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub(monkeypatch, [FILTER], [])

    def fail(*_: Any, **__: Any) -> None:
        raise RuntimeError("embedding endpoint down")

    monkeypatch.setattr(module, "get_embeddings", fail)
    result = _run(_state(FakeConnector([1])))
    assert result["path_state"]["semantic_ids"] == {}
    assert 'filter "riset"."topik" with ILIKE' in result["semantic_instructions"]


def test_all_reviewed_matching_at_the_limit_is_flagged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "RECALL_K", 3)
    monkeypatch.setattr(module, "VERIFY_K", 2)
    _stub(monkeypatch, [FILTER], [1, 2])
    state = _state(FakeConnector([1, 2, 3]))
    _run(state)
    assert SEMANTIC_TRUNCATED_NOTE in str(state["path_state"].get("thoughts_log"))


def test_partial_match_is_not_flagged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "RECALL_K", 3)
    monkeypatch.setattr(module, "VERIFY_K", 2)
    _stub(monkeypatch, [FILTER], [1])
    state = _state(FakeConnector([1, 2, 3]))
    _run(state)
    assert not state["path_state"].get("thoughts_log")


def test_rrf_ranks_rows_found_by_both_arms_first() -> None:
    vector = [{"id": 1}, {"id": 2}, {"id": 3}]
    bm25 = [{"id": 3}, {"id": 4}]
    # 2 and 4 are both second in their arm: the tie keeps the vector order.
    assert [row["id"] for row in rrf(vector, bm25)] == [3, 1, 2, 4]


def test_a_table_with_a_bm25_column_is_searched_hybrid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub(monkeypatch, [FILTER], [1, 2])
    connector = FakeConnector([7, 8], bm25_ids=[9, 8])
    result = _run(_state(connector))
    # 8 is in both arms, so it ranks first and is candidate 1.
    assert result["path_state"]["semantic_ids"] == {"__SEMANTIC_1__": "8, 7"}
    bm25_sql, parameters = connector.call("|||")
    assert '"topik_bm25" ||| %s::text' in bm25_sql
    assert parameters == ["pariwisata", module.RECALL_K]


def test_a_failed_bm25_arm_keeps_the_vector_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub(monkeypatch, [FILTER], [1])

    def fail(*_: Any, **__: Any) -> None:
        raise RuntimeError("no bm25 index")

    monkeypatch.setattr(module, "keyword_rows", fail)
    result = _run(_state(FakeConnector([7], bm25_ids=[9])))
    assert result["path_state"]["semantic_ids"] == {"__SEMANTIC_1__": "7"}


@pytest.mark.parametrize(
    ("value", "expected"), [(5, "5"), ("a'b", "'a''b'"), ("uuid-1", "'uuid-1'")]
)
def test_sql_literal_quotes_text_only(value: Any, expected: str) -> None:
    assert sql_literal(value) == expected
