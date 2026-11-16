"""The direct vector search: which filters it takes, and the hits it builds."""

import pytest

from auto_ontology.vdb.vector_query import _hit, metadata_filter

COLUMNS = ("database_name", "label")


def test_no_filter_searches_the_whole_collection() -> None:
    for where in (None, {}):
        where_sql, params = metadata_filter(where, COLUMNS)
        assert where_sql.as_string(None) == ""
        assert params == []


def test_string_values_become_equality_on_metadata_columns() -> None:
    where_sql, params = metadata_filter(
        {"label": "Table", "database_name": "shop"}, COLUMNS
    )
    assert where_sql.as_string(None) == ' WHERE "label" = %s AND "database_name" = %s'
    assert params == ["Table", "shop"]


@pytest.mark.parametrize(
    "where",
    [
        {"schema_name": "public"},  # not a metadata column
        {"label": ["Table", "Column"]},  # langchain treats a list as $eq
        {"label": {"$in": ["Table"]}},  # an operator
    ],
)
def test_anything_else_is_left_to_langchain(where: dict) -> None:
    assert metadata_filter(where, COLUMNS) is None


def test_a_hit_carries_the_json_metadata_with_the_columns_on_top() -> None:
    row = {
        "content": "orders table",
        "langchain_metadata": {"id": "orders", "label": "stale"},
        "database_name": "shop",
        "label": "Table",
        "distance": 0.25,
    }
    assert _hit(row, COLUMNS) == {
        "text": "orders table",
        "metadata": {"id": "orders", "label": "Table", "database_name": "shop"},
        "_distance": 0.25,
    }


def test_a_row_without_json_metadata_still_has_its_columns() -> None:
    row = {
        "content": "x",
        "langchain_metadata": None,
        "database_name": "shop",
        "label": "Table",
        "distance": 0,
    }
    assert _hit(row, COLUMNS)["metadata"] == {"database_name": "shop", "label": "Table"}
