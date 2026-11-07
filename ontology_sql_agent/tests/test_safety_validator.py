# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from ontology_sql_agent.nodes.safety_validator import read_only_problem


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "WITH t AS (SELECT 1 AS a) SELECT a FROM t",
        "SELECT a FROM t UNION SELECT a FROM u",
        # A write word inside a literal is data; the classic regex rejected this.
        "SELECT judul FROM berita WHERE judul ILIKE '%update%'",
    ],
)
def test_read_only_queries_pass(sql: str) -> None:
    assert read_only_problem(sql, "postgres") == ""


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM t",
        "DROP TABLE t",
        "UPDATE t SET a = 1",
        "SELECT 1; DROP TABLE t",
        "SELECT * INTO copy_t FROM t",
        "WITH gone AS (DELETE FROM t RETURNING a) SELECT a FROM gone",
        "not sql at all (",
    ],
)
def test_writes_and_unparseable_sql_are_rejected(sql: str) -> None:
    assert read_only_problem(sql, "postgres") != ""
