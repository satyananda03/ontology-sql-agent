# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any

import pytest

from ontology_sql_agent import workflow
from ontology_sql_agent.nodes.repair import INFO_NOT_FOUND
from ontology_sql_agent.state import State

ROWS = [{"nama": "A"}]


class FakeNodes:
    """Replaces every LLM and database node, scripting what each returns."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.visits: list[str] = []
        self.tables: list[str] = ["t"]
        self.syntax: list[dict[str, Any]] = [{"sql_syntax_status": "valid"}]
        self.results: list[list[dict]] = [ROWS]
        for name in ("ontology_context", "semantic_search", "sql_generator"):
            monkeypatch.setattr(workflow, name, getattr(self, name))
        monkeypatch.setattr(workflow, "sql_syntax_validator", self.sql_syntax_validator)
        monkeypatch.setattr(workflow, "sql_executor", self.sql_executor)
        monkeypatch.setattr(workflow, "value_probe", self.value_probe)

    def ontology_context(self, state: State) -> dict[str, Any]:
        self.visits.append("context")
        if not self.tables:
            return {"selected_table": [], "error": "none", "error_code": INFO_NOT_FOUND}
        return {"selected_table": self.tables}

    def semantic_search(self, state: State) -> dict[str, Any]:
        return {}

    def sql_generator(self, state: State) -> dict[str, Any]:
        self.visits.append("generate")
        return {
            "sql_query": "SELECT nama FROM t",
            "raw_sql_query": "SELECT nama FROM t",
        }

    def sql_syntax_validator(self, state: State) -> dict[str, Any]:
        return self.syntax.pop(0) if len(self.syntax) > 1 else self.syntax[0]

    def sql_executor(self, state: State) -> dict[str, Any]:
        rows = self.results.pop(0) if len(self.results) > 1 else self.results[0]
        return {
            "sql_execution_status": "success",
            "sql_execution_result": {"success": True, "data": rows},
        }

    def value_probe(self, state: State) -> dict[str, Any]:
        self.visits.append("probe")
        return {
            "value_probed": True,
            "retry_feedback": "<previous_attempt/>",
            "retry_count": 1,
        }


def _run() -> dict[str, Any]:
    graph = workflow.create_workflow().compile()
    return graph.invoke(State(user_query="q"), config={"recursion_limit": 50})


def test_answers_on_the_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    nodes = FakeNodes(monkeypatch)
    state = _run()
    assert nodes.visits == ["context", "generate"]
    assert state["answer"].startswith("ROWS : 1")


def test_empty_result_is_probed_then_regenerated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodes = FakeNodes(monkeypatch)
    nodes.results = [[], ROWS]
    state = _run()
    assert nodes.visits == ["context", "generate", "probe", "generate"]
    assert state["answer"].startswith("ROWS : 1")


def test_fixable_error_is_repaired(monkeypatch: pytest.MonkeyPatch) -> None:
    nodes = FakeNodes(monkeypatch)
    nodes.syntax = [
        {"sql_syntax_status": "invalid", "error": "bad", "error_code": "42703"},
        {"sql_syntax_status": "valid"},
    ]
    state = _run()
    assert nodes.visits == ["context", "generate", "generate"]
    assert state["retry_count"] == 1


def test_no_tables_ends_in_a_failure_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    nodes = FakeNodes(monkeypatch)
    nodes.tables = []
    state = _run()
    assert nodes.visits == ["context"]
    assert state["answer"].startswith("STATUS: error")


def test_a_write_statement_stops_without_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodes = FakeNodes(monkeypatch)
    monkeypatch.setattr(
        nodes,
        "sql_generator",
        lambda state: {"sql_query": "DELETE FROM t", "raw_sql_query": "DELETE FROM t"},
    )
    monkeypatch.setattr(workflow, "sql_generator", nodes.sql_generator)
    state = _run()
    assert state["sql_safety_status"] == "unsafe"
    assert state.get("answer") is None
