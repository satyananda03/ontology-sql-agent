# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest

from auto_ontology.connectors.registry import (
    parse_connection_strings,
    source_connection_string,
)


def test_parse_connection_strings_accepts_commas_and_newlines() -> None:
    raw = """
        postgresql://localhost/first
        clickhouse://localhost/second,

        snowflake://account?database=third
    """

    assert parse_connection_strings(raw) == [
        "postgresql://localhost/first",
        "clickhouse://localhost/second",
        "snowflake://account?database=third",
    ]


def test_source_connection_string_is_the_one_configured_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CONNECTION_STRINGS", " postgresql://u:p@h/sales \n")

    assert source_connection_string() == "postgresql://u:p@h/sales"


def test_source_connection_string_is_none_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CONNECTION_STRINGS", raising=False)

    assert source_connection_string() is None


def test_more_than_one_source_database_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CONNECTION_STRINGS", "postgresql://h/a,postgresql://h/b")

    with pytest.raises(ValueError, match="exactly one source database"):
        source_connection_string()
