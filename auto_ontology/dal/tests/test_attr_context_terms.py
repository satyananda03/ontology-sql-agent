"""``fetch_attr_column_contexts`` keeps every Term of an attribute; no database needed."""

import pytest

pytest.importorskip("sqlalchemy")

from auto_ontology.dal import attributes as a  # noqa: E402


def _row(term_id: str | None, column: str = "owner_col") -> dict:
    return {
        "attr_id": "attr-1",
        "attr_name": "Budget",
        "attr_description": "",
        "datatype": "numeric",
        "col_id": column,
        "col_name": column,
        "table_id": "t1",
        "table_name": "festival",
        "schema_name": "public",
        "database_name": "db",
        "term_name": "Finance",
        "term_id": term_id,
    }


class _FakeStore:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.sql = ""

    def query_read(self, statement) -> list[dict]:
        self.sql = str(statement.compile())
        return self.rows


def test_an_attribute_in_several_terms_keeps_all_their_ids(monkeypatch) -> None:
    # One row per (link, term): two Terms, the second repeated by a referencing link.
    fake = _FakeStore(
        [_row("term-a"), _row("term-b"), _row("term-b", column="ref_col"), _row(None)]
    )
    monkeypatch.setattr(a, "store", lambda: fake)

    context = a.fetch_attr_column_contexts(["attr-1"], database_name=None)["attr-1"]

    assert context["term_ids"] == ["term-a", "term-b"]
    assert context["col_name"] == "owner_col"  # the first (owning) row still wins
    assert "term_id" in fake.sql
