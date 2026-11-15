# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""An ingest pass records how it ended, for ``GET /ingest/status``."""

import asyncio
from types import SimpleNamespace

import pytest

from auto_ontology.ingestion_service import data_scheduler
from auto_ontology.ingestion_service.data_scheduler import DataScheduler


def _run_pass(
    monkeypatch: pytest.MonkeyPatch, connectors: list, run_ingest
) -> DataScheduler:
    async def no_rules(_label: str) -> None:
        return None

    monkeypatch.setattr(data_scheduler, "invalidate_connectors_cache", lambda: None)
    monkeypatch.setattr(data_scheduler, "get_connectors", lambda: connectors)
    monkeypatch.setattr(data_scheduler, "run_ingest", run_ingest)
    monkeypatch.setattr(data_scheduler, "replay_rules_in_thread", no_rules)
    scheduler = DataScheduler()
    asyncio.run(scheduler._run_pass())
    return scheduler


def _fail(_connector: object) -> None:
    raise RuntimeError("source down")


def test_success_is_recorded_without_a_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scheduler = _run_pass(
        monkeypatch, [SimpleNamespace(database_name="sales")], lambda _c: None
    )

    assert scheduler.last_success_at is not None
    assert scheduler.last_failure_at is None


def test_a_failed_connection_is_a_failed_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    connectors = [SimpleNamespace(database_name="sales")]
    scheduler = _run_pass(monkeypatch, connectors, _fail)

    assert scheduler.last_failure_at is not None
    assert scheduler.last_success_at is None


def test_no_connection_is_a_failed_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduler = _run_pass(monkeypatch, [], lambda _c: None)

    assert scheduler.last_failure_at is not None


def test_an_unhandled_error_is_a_failed_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_registry() -> list:
        raise RuntimeError("bad config")

    monkeypatch.setattr(data_scheduler, "invalidate_connectors_cache", lambda: None)
    monkeypatch.setattr(data_scheduler, "get_connectors", broken_registry)
    scheduler = DataScheduler()
    asyncio.run(scheduler._run_pass())

    assert scheduler.last_failure_at is not None
