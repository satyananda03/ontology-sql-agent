# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from auto_ontology.connectors.base import StatementTimeout
from ontology_sql_agent import db
from ontology_sql_agent.nodes.repair import (
    INFO_NOT_FOUND,
    MAX_RETRIES,
    route_failure,
    sql_failure,
    sql_repair,
)
from ontology_sql_agent.state import State
from ontology_sql_agent.utils import classify_error, format_query_results_for_llm


class PgError(Exception):
    """Shaped like a psycopg error: an SQLSTATE and diagnostics."""

    def __init__(self, message: str, sqlstate: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.sqlstate = sqlstate
        self.diag = SimpleNamespace(message_hint=hint)


class FakeConnector:
    def __init__(self, result: pd.DataFrame | Exception) -> None:
        self.result = result
        self.statements: list[str] = []

    def execute(self, sql: str, parameters: list | None = None) -> pd.DataFrame:
        self.statements.append(sql)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_postgres_hint_is_kept_for_the_generator() -> None:
    error = PgError('column "nma" does not exist', "42703", 'Perhaps "nama".')
    assert db.db_error(error) == (
        "42703",
        'column "nma" does not exist\nHINT: Perhaps "nama".',
    )


def test_timeout_is_classified_as_fixable_not_transient() -> None:
    code, _ = db.db_error(StatementTimeout(30.0))
    assert classify_error(code) == "fixable"


def test_explain_checks_without_running() -> None:
    connector = FakeConnector(pd.DataFrame())
    assert db.explain("SELECT 1", connector)["valid_syntax"]
    assert connector.statements == ["EXPLAIN SELECT 1"]


def test_explain_reports_the_sqlstate() -> None:
    result = db.explain("SELECT x", FakeConnector(PgError("bad", "42703")))
    assert result == {"valid_syntax": False, "error": "bad", "error_code": "42703"}


def test_query_nulls_reach_the_caller_as_none() -> None:
    frame = pd.DataFrame({"a": [1.5, None], "b": ["x", None]})
    result = db.run_query(" SELECT a, b FROM t ", FakeConnector(frame))
    assert result["success"] and result["row_count"] == 2
    assert result["data"][1] == {"a": None, "b": None}
    assert result["query_executed"] == "SELECT a, b FROM t"


@pytest.mark.parametrize(
    ("sqlstate", "kind"),
    [
        (None, "transient"),
        ("08006", "transient"),
        ("40P01", "transient"),
        ("42501", "fatal"),
        ("42703", "fixable"),
        ("22P02", "fixable"),
        ("57014", "fixable"),
        ("XX000", "fatal"),
    ],
)
def test_classify_error_is_unchanged(sqlstate: str | None, kind: str) -> None:
    assert classify_error(sqlstate) == kind


def _state(**fields: object) -> State:
    return State(user_query="q", **fields)


def test_first_fixable_error_is_repaired() -> None:
    assert route_failure(_state(error="e", error_code="42703")) == "repair"


def test_repeated_missing_column_renavigates_once() -> None:
    state = _state(error="e", last_error="e", error_code="42703")
    assert route_failure(state) == "renavigate"
    state.renavigation_count = 1
    assert route_failure(state) == "fail"


def test_exhausted_retries_stop() -> None:
    state = _state(error="new", error_code="22P02", retry_count=MAX_RETRIES)
    assert route_failure(state) == "fail"


def test_non_fixable_errors_fail_immediately() -> None:
    assert route_failure(_state(error="e", error_code="42501")) == "fail"


def test_repair_feedback_carries_error_sql_and_hint() -> None:
    state = _state(error="boom", error_code="42703", raw_sql_query="SELECT x")
    update = sql_repair(state)
    assert update["retry_count"] == 1
    assert "boom" in update["retry_feedback"]
    assert "SELECT x" in update["retry_feedback"]
    assert "Pakai persis nama" in update["retry_feedback"]


def test_missing_information_is_reported_as_unavailable() -> None:
    answer = sql_failure(_state(error="none", error_code=INFO_NOT_FOUND))["answer"]
    assert answer.startswith("STATUS: error")
    assert "tidak ada di tabel mana pun" in answer


def test_results_are_capped_with_a_note() -> None:
    rows = [{"a": i} for i in range(3)]
    text = format_query_results_for_llm({"success": True, "data": rows}, max_rows=2)
    assert text.startswith("CATATAN : hanya 2 dari 3 baris")
    assert '{"a": 2}' not in text
