"""Tests for reading instance-wide feature flags."""

from contextlib import contextmanager
from typing import Iterator

import pytest

from auto_ontology.infra import feature_flags
from auto_ontology.infra.feature_flags import (
    get_sql_query_timeout_seconds,
    is_distinct_value_probing_enabled,
    read_configuration_flag,
    read_configuration_int,
)


class _Reads:
    """Stands in for the stored values: records the keys read, answers *stored*."""

    def __init__(self, stored: str | None) -> None:
        self.stored = stored
        self.keys: list[str] = []

    def __call__(self, key: str) -> str | None:
        self.keys.append(key)
        return self.stored


@contextmanager
def _patched(monkeypatch: pytest.MonkeyPatch, stored: str | None) -> Iterator[_Reads]:
    reads = _Reads(stored)
    monkeypatch.setattr(feature_flags.settings_dal, "read_configuration", reads)
    yield reads


@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        ("true", True),
        ("TRUE", True),
        (" true ", True),
        ("false", False),
        ("FALSE", False),
    ],
)
def test_stored_value_wins_over_the_default(
    monkeypatch: pytest.MonkeyPatch, stored: str, expected: bool
) -> None:
    # Casing and stray whitespace must not flip a flag; the frontend writes
    # lowercase, but nothing stops an operator editing the row by hand.
    with _patched(monkeypatch, stored):
        assert read_configuration_flag("k", default=not expected) is expected


@pytest.mark.parametrize("stored", ["", "1", "yes", "null", "  "])
def test_unrecognised_value_falls_back_to_the_default(
    monkeypatch: pytest.MonkeyPatch, stored: str
) -> None:
    """Must agree with the frontend, which reads opt-out flags as != 'false'.

    Treating junk as False would render the toggle ON while the backend
    silently stopped probing -- the divergence the route comment rules out.
    """
    with _patched(monkeypatch, stored):
        assert read_configuration_flag("k", default=True) is True
        assert read_configuration_flag("k", default=False) is False


def test_distinct_probing_survives_a_junk_row(monkeypatch: pytest.MonkeyPatch) -> None:
    with _patched(monkeypatch, ""):
        assert is_distinct_value_probing_enabled() is True


def test_missing_row_falls_back_to_the_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _patched(monkeypatch, None):
        assert read_configuration_flag("k", default=True) is True
        assert read_configuration_flag("k", default=False) is False


def test_db_error_falls_back_to_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    # Before the first migration the table does not exist. That must
    # not crash a service at startup, and must not silently flip an opt-out
    # flag to off.
    def _boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("relation does not exist")

    monkeypatch.setattr(feature_flags.settings_dal, "read_configuration", _boom)

    assert read_configuration_flag("k", default=True) is True
    assert read_configuration_flag("k", default=False) is False


def test_distinct_probing_defaults_to_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Opt-out: upgrading an existing instance must not silently stop probing."""
    with _patched(monkeypatch, None) as reads:
        assert is_distinct_value_probing_enabled() is True
    assert reads.keys == ["distinct_value_probing_enabled"]


def test_distinct_probing_honours_an_explicit_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _patched(monkeypatch, "false"):
        assert is_distinct_value_probing_enabled() is False


@pytest.mark.parametrize(
    ("stored", "expected"),
    [("45", 45), (" 45 ", 45), ("1", 1), ("3600", 3600)],
)
def test_sql_query_timeout_honours_a_stored_value(
    monkeypatch: pytest.MonkeyPatch, stored: str, expected: int
) -> None:
    with _patched(monkeypatch, stored) as reads:
        assert get_sql_query_timeout_seconds() == expected
    assert reads.keys == ["sql_query_timeout_seconds"]


@pytest.mark.parametrize("stored", ["", "abc", "1.5", "0", "-5", "3601"])
def test_unusable_int_falls_back_to_the_default(
    monkeypatch: pytest.MonkeyPatch, stored: str
) -> None:
    with _patched(monkeypatch, stored):
        assert read_configuration_int("k", default=30, minimum=1, maximum=3600) == 30


def test_sql_query_timeout_defaults_to_30_seconds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An instance running without the frontend never writes the row."""
    with _patched(monkeypatch, None):
        assert get_sql_query_timeout_seconds() == 30
