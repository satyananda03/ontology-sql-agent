"""The settings readers borrow from the DAL pool and never raise."""

from typing import Any

import pytest

from auto_ontology.infra.postgres import FRONTEND_SCHEMA
from auto_ontology.server import settings_dal


class _Store:
    """Stands in for the DAL handle: canned rows, or a failure."""

    def __init__(
        self, rows: list[dict[str, Any]] | None = None, error: Exception | None = None
    ) -> None:
        self.rows = rows or []
        self.error = error
        self.statements: list[str] = []

    def query_read(self, statement: str) -> list[dict[str, Any]]:
        if self.error:
            raise self.error
        self.statements.append(statement)
        return self.rows


def _use(monkeypatch: pytest.MonkeyPatch, store: _Store) -> _Store:
    monkeypatch.setattr(settings_dal, "store", lambda: store)
    return store


def test_acronyms_are_read_through_the_pooled_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    glossary = [{"name": "PR", "description": "pelaku kreatif"}]
    store = _use(monkeypatch, _Store(rows=glossary))

    assert settings_dal.fetch_acronyms() == glossary
    assert f"{FRONTEND_SCHEMA}.acronyms" in store.statements[0]


def test_custom_prompts_are_joined_and_blank_ones_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [{"content": "first"}, {"content": ""}, {"content": "second"}]
    _use(monkeypatch, _Store(rows=rows))

    assert settings_dal.fetch_custom_prompts() == "first\n\nsecond"


def test_a_store_failure_leaves_the_readers_empty_handed_not_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use(monkeypatch, _Store(error=RuntimeError("database unreachable")))

    assert settings_dal.fetch_acronyms() == []
    assert settings_dal.fetch_custom_prompts() == ""
