# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any

import pytest

from sql_agent import service
from sql_agent.nodes.repair import INFO_NOT_FOUND
from sql_agent.semantic_rows import SEMANTIC_TRUNCATED_NOTE


def _done(rows: list[dict], **fields: Any) -> dict[str, Any]:
    return {
        "sql_query": "SELECT 1",
        "answer": "ROWS : …",
        "sql_execution_status": "success",
        "sql_execution_result": {"data": rows},
        **fields,
    }


def test_rows_are_ok_with_their_count() -> None:
    result = service.to_query_result(_done([{"a": 1}, {"a": 2}]))
    assert (result.status, result.row_count, result.truncated) == ("ok", 2, False)


def test_no_rows_is_empty() -> None:
    assert service.to_query_result(_done([])).status == "empty"


def test_rows_beyond_the_cap_are_marked_truncated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service, "max_rows", lambda: 1)
    assert service.to_query_result(_done([{"a": 1}, {"a": 2}])).truncated


def test_semantic_cut_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    ontology = {"path_state": {"thoughts_log": [{"text": SEMANTIC_TRUNCATED_NOTE}]}}
    result = service.to_query_result(_done([{"a": 1}], ontology=ontology))
    assert result.truncated and result.text.startswith("CATATAN : pencarian topik")


@pytest.mark.parametrize(
    ("code", "status"),
    [(INFO_NOT_FOUND, "unanswerable"), ("42P01", "unanswerable"), ("08006", "error")],
)
def test_failures_split_into_unanswerable_and_error(code: str, status: str) -> None:
    state = {
        "answer": "STATUS: error",
        "error_code": code,
        "sql_execution_status": None,
    }
    assert service.to_query_result(state).status == status


def test_a_stopped_write_asks_the_caller_to_clarify() -> None:
    result = service.to_query_result({"answer": None, "error": "Only SELECT"})
    assert result.status == "error" and "Only SELECT" in result.text


def test_a_crash_becomes_a_tool_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def crash(*_: Any, **__: Any) -> None:
        raise RuntimeError("store down")

    monkeypatch.setattr(service, "run", crash)
    result = service.answer("q")
    assert result.status == "error" and "store down" in result.text


def test_error_says_the_wording_was_not_the_cause() -> None:
    result = service.render_error("boom")
    assert result.status == "error"
    assert "boom" in result.text
    assert "bukan karena kata-kata pertanyaan" in result.text
