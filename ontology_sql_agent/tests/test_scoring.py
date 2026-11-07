# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from decimal import Decimal

import yaml

from ontology_sql_agent.eval.report import outcome_cell
from ontology_sql_agent.eval.run import GOLDEN
from ontology_sql_agent.eval.scoring import (
    results_match,
    retrieval_recall,
    tables_in_sql,
)

GOLD = [{"nama": "Ayu"}, {"nama": "Budi"}]


def test_order_column_names_and_case_do_not_matter() -> None:
    predicted = [{"researcher": "budi "}, {"researcher": "AYU"}]
    assert results_match(GOLD, predicted)


def test_extra_columns_are_allowed() -> None:
    predicted = [{"n": "Ayu", "kota": "x"}, {"n": "Budi", "kota": "y"}]
    assert results_match(GOLD, predicted)


def test_missing_or_extra_rows_are_wrong() -> None:
    assert not results_match(GOLD, [{"n": "Ayu"}])
    assert not results_match(GOLD, [{"n": "Ayu"}, {"n": "Budi"}, {"n": "Citra"}])


def test_a_duplicate_from_a_bad_join_is_wrong() -> None:
    assert not results_match(GOLD, [{"n": "Ayu"}, {"n": "Ayu"}])


def test_a_missing_column_is_wrong() -> None:
    assert not results_match(GOLD, [{"keahlian": "x"}, {"keahlian": "y"}])


def test_equal_numbers_match_across_types() -> None:
    assert results_match([{"t": 3}], [{"t": Decimal("3.00")}])
    assert results_match([{"t": 3.0}], [{"t": 3}])
    assert not results_match([{"t": 3}], [{"t": 4}])


def test_both_empty_match() -> None:
    assert results_match([], [])


def test_tables_exclude_cte_names() -> None:
    sql = "WITH c AS (SELECT 1 FROM s.a) SELECT 1 FROM c JOIN s.b ON true"
    assert tables_in_sql(sql) == {"a", "b"}


def test_recall_is_the_share_of_needed_tables_in_context() -> None:
    sql = "SELECT 1 FROM a JOIN b ON true"
    assert retrieval_recall(sql, ["a", "z"]) == 0.5
    assert retrieval_recall(sql, ["a", "b"]) == 1.0


def test_golden_file_is_well_formed() -> None:
    questions = yaml.safe_load(GOLDEN.read_text())["questions"]
    ids = [item["id"] for item in questions]
    assert len(ids) == len(set(ids))
    assert len(questions) >= 40
    for item in questions:
        assert item["question"].strip() and item["category"] and "sql" in item
        if item["sql"]:
            assert tables_in_sql(item["sql"])


def test_an_unanswered_question_is_not_reported_as_wrong() -> None:
    assert outcome_cell(None) == "-"
    assert outcome_cell(False) == "WRONG"
    assert outcome_cell(True) == "ok"
