from auto_ontology.server.models import ColumnSummary, TableColumns


def test_an_embedding_column_is_marked_in_the_response() -> None:
    page = TableColumns.model_validate(
        {
            "columns": [
                {"id": "c1", "column_name": "teks", "data_type": "text"},
                {"id": "c2", "column_name": "teks_vector", "data_type": "vector"},
                {"id": "c3", "column_name": "note", "data_type": None},
            ]
        }
    )

    assert [c["is_embedding"] for c in page.model_dump()["columns"]] == [
        False,
        True,
        False,
    ]


def test_every_pgvector_type_counts_as_an_embedding() -> None:
    for data_type in ("vector", "halfvec", "sparsevec"):
        assert ColumnSummary(id="c", data_type=data_type).is_embedding
