"""The one status row: what each outcome overwrites, and that reads never raise."""

from datetime import datetime, timezone
from typing import Any

import pytest
from sqlalchemy.dialects import postgresql

from auto_ontology.dal import semantic_compilation_status as status


class _Store:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = rows or []
        self.writes: list[str] = []

    def query_write(self, statement: Any) -> None:
        self.writes.append(str(statement.compile(dialect=postgresql.dialect())))

    def query_read(self, _statement: Any) -> list[dict[str, Any]]:
        return self.rows


def _use(monkeypatch: pytest.MonkeyPatch, store: _Store) -> _Store:
    monkeypatch.setattr(status, "store", lambda: store)
    return store


def _update_clause(sql: str) -> str:
    return sql.split("DO UPDATE SET", 1)[1]


def test_a_success_clears_the_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _use(monkeypatch, _Store())

    status.record_outcome(status.RUN_SUCCEEDED)

    update = _update_clause(store.writes[0])
    assert "last_success_at = now()" in update
    assert "last_failure_at = " in update


def test_a_failure_keeps_the_last_success(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _use(monkeypatch, _Store())

    status.record_outcome(status.RUN_FAILED)

    update = _update_clause(store.writes[0])
    assert "last_failure_at = now()" in update
    assert "last_success_at" not in update


def test_an_unknown_outcome_is_refused() -> None:
    with pytest.raises(ValueError):
        status.record_outcome("aborted")


def test_no_row_yet_reads_as_never(monkeypatch: pytest.MonkeyPatch) -> None:
    _use(monkeypatch, _Store())

    assert status.last_outcomes() == {"last_success_at": None, "last_failure_at": None}


def test_the_row_reads_back_as_iso_8601(monkeypatch: pytest.MonkeyPatch) -> None:
    moment = datetime(2026, 11, 15, 8, 0, tzinfo=timezone.utc)
    _use(monkeypatch, _Store([{"last_success_at": moment, "last_failure_at": None}]))

    assert status.last_outcomes() == {
        "last_success_at": moment.isoformat(),
        "last_failure_at": None,
    }
