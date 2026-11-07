# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""The Postgres connector honours ``execute(..., timeout_s=...)``.

The text-to-SQL agent caps each statement at the SQL Query Timeout from Agent
Settings, but only on connectors advertising ``supports_statement_timeout``.
The connector is checked against a fake driver for the setting it sends, plus a
live Postgres check when a fixture database is reachable.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any, Iterator

import psycopg
import pytest

from auto_ontology.connectors.base import StatementTimeout
from auto_ontology.connectors.postgres import PostgresDatabase
from auto_ontology.connectors.registry import CONNECTOR_REGISTRY


def test_every_registered_connector_supports_a_timeout() -> None:
    missing = [
        name
        for name, cls in CONNECTOR_REGISTRY.items()
        if getattr(cls, "supports_statement_timeout", False) is not True
    ]
    assert missing == []


def test_timeout_message_is_not_mistaken_for_a_dead_connection() -> None:
    """A cancelled query should be rewritten, not reported as unreachable."""
    from auto_ontology.connectors.db_errors import is_infrastructure_error

    assert not is_infrastructure_error(str(StatementTimeout(30)), "SELECT 1")


@pytest.mark.parametrize(
    ("elapsed_s", "points_at"),
    [
        (None, "Agent Settings"),
        (300.4, "Agent Settings"),
        # Cancelled at 10s under a 300s cap: the warehouse's own limit fired.
        (10.0, "database or warehouse"),
    ],
)
def test_timeout_message_names_the_limit_that_fired(
    elapsed_s: float | None, points_at: str
) -> None:
    message = str(StatementTimeout(300, elapsed_s=elapsed_s))

    assert points_at in message
    if points_at != "Agent Settings":
        assert "will not help" in message


# ----------------------------------------------------------------------
# Postgres
# ----------------------------------------------------------------------


class _PgConnection:
    def __init__(self) -> None:
        self.log: list[Any] = []

    @contextmanager
    def transaction(self) -> Iterator[None]:
        self.log.append("BEGIN")
        yield
        self.log.append("COMMIT")

    def execute(self, sql: str, params: Any = None) -> None:
        self.log.append((sql, params))

    def cursor(self, **kwargs: Any) -> "_PgCursor":
        return _PgCursor(self)


class _PgCursor:
    description = [("v",)]

    def __init__(self, conn: _PgConnection) -> None:
        self._conn = conn

    def __enter__(self) -> "_PgCursor":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, sql: str, params: Any = None) -> None:
        self._conn.log.append(("query", sql))

    def fetchall(self) -> list[dict[str, int]]:
        return [{"v": 1}]


class _PgPool:
    def __init__(self) -> None:
        self.conn = _PgConnection()

    @contextmanager
    def connection(self) -> Iterator[_PgConnection]:
        yield self.conn


def _fake_postgres() -> tuple[PostgresDatabase, _PgConnection]:
    database = PostgresDatabase.__new__(PostgresDatabase)
    pool = _PgPool()
    database._pool = pool  # noqa: SLF001 - test double for the pool
    return database, pool.conn


def test_postgres_scopes_the_timeout_to_one_transaction() -> None:
    database, conn = _fake_postgres()

    database.execute("SELECT 1", timeout_s=1.5)

    assert conn.log == [
        "BEGIN",
        ("SELECT set_config('statement_timeout', %s, true)", ("1500ms",)),
        ("query", "SELECT 1"),
        "COMMIT",
    ]


def test_postgres_without_timeout_sends_no_setting() -> None:
    database, conn = _fake_postgres()

    database.execute("SELECT 1")

    assert conn.log == [("query", "SELECT 1")]


def test_live_postgres_cancels_and_does_not_leak_the_cap() -> None:
    if not os.environ.get("POSTGRES_USER"):
        pytest.skip("POSTGRES_* not set")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    try:
        database = PostgresDatabase(
            f"postgresql://{user}:{password}@{host}:{port}/postgres"
        )
    except Exception as exc:  # noqa: BLE001 — any failure means "no fixture DB"
        pytest.skip(f"postgres not reachable: {exc}")
    try:
        with pytest.raises(StatementTimeout):
            database.execute("SELECT pg_sleep(5)", timeout_s=0.3)
        # The pool holds one idle connection; the cap must not have stuck to it.
        setting = database.execute("SHOW statement_timeout").iloc[0, 0]
        assert setting == "0"
    finally:
        database.close()


# ----------------------------------------------------------------------
# Every engine's cancellation surfaces as StatementTimeout
# ----------------------------------------------------------------------
#
# Callers recognise a timeout by type: semantic compilation's sampling circuit
# breaker counts ``TimeoutError`` and no server-reported cancellation message,
# so an engine whose cancellation stayed a driver error would never trip it.


def test_sampling_breaker_counts_a_statement_timeout() -> None:
    from auto_ontology.semantic.visit_enter import _SamplingCircuitBreaker

    breaker = _SamplingCircuitBreaker()
    connector = SimpleNamespace(database_name="warehouse")

    assert breaker.record_failure(connector, StatementTimeout(120)) is True


def _raising_postgres(error: BaseException) -> PostgresDatabase:
    database, conn = _fake_postgres()

    class _Cursor(_PgCursor):
        def execute(self, sql: str, params: Any = None) -> None:
            raise error

    conn.cursor = lambda **kwargs: _Cursor(conn)  # type: ignore[method-assign]
    return database


def test_postgres_statement_timeout_becomes_statement_timeout() -> None:
    database = _raising_postgres(
        psycopg.errors.QueryCanceled("canceling statement due to statement timeout")
    )

    with pytest.raises(StatementTimeout) as caught:
        database.execute("SELECT 1", timeout_s=30)
    assert caught.value.timeout_s == 30


def test_postgres_other_cancellation_is_left_alone() -> None:
    """pg_cancel_backend() is an operator's decision, not our cap."""
    database = _raising_postgres(
        psycopg.errors.QueryCanceled("canceling statement due to user request")
    )

    with pytest.raises(psycopg.errors.QueryCanceled):
        database.execute("SELECT 1", timeout_s=30)
