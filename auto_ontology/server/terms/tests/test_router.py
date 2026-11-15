"""PATCH /terms/{id}: a synonym edit must reach the vector store."""

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from auto_ontology.server.terms import router as module


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(module.router)
    return TestClient(app)


def _row(**changes: object) -> dict:
    return {"id": "t1", "name": "Order", "old_name": "Order", "synonyms": [], **changes}


@patch.object(module.terms_dal, "get_term_certification", return_value="pending")
@patch.object(module.term_service, "refresh_term_embeddings")
@patch.object(module.terms_dal, "update_term")
def test_editing_synonyms_re_embeds_the_term_and_its_attributes(
    update: MagicMock, refresh: MagicMock, _certification: MagicMock
) -> None:
    """Every ColumnAttribute's embedded text carries the Term's synonyms."""
    update.return_value = _row(synonyms=["pesanan"])

    response = _client().patch("/terms/t1", json={"synonyms": [" pesanan "]})

    assert response.status_code == 200
    assert response.json()["data"]["synonyms"] == ["pesanan"]
    assert update.call_args.kwargs["synonyms"] == ["pesanan"]
    refresh.assert_called_once_with("t1", refresh_dependent_attrs=True)


@patch.object(module.terms_dal, "get_term_certification", return_value="pending")
@patch.object(module.term_service, "refresh_term_embeddings")
@patch.object(module.terms_dal, "update_term")
def test_other_edits_leave_synonyms_alone(
    update: MagicMock, refresh: MagicMock, _certification: MagicMock
) -> None:
    update.return_value = _row(synonyms=["pesanan"])

    _client().patch("/terms/t1", json={"name_certified": True})

    assert update.call_args.kwargs["synonyms"] is None
    refresh.assert_not_called()


def test_a_blank_or_oversized_synonym_is_refused() -> None:
    assert _client().patch("/terms/t1", json={"synonyms": [" "]}).status_code == 422
    too_many = {"synonyms": [f"s{i}" for i in range(51)]}
    assert _client().patch("/terms/t1", json=too_many).status_code == 422
