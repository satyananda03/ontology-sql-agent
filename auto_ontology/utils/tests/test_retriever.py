"""Retriever's query embedding: computed once per text."""

from typing import Any

import pytest

from auto_ontology.utils import retriever as retriever_mod
from auto_ontology.utils.embedding import EmbedParams


class _FakeVDB:
    def retrieval(self, queries: list, top_k: int, where: Any) -> list[list[dict]]:
        return [[] for _ in queries]


@pytest.fixture(autouse=True)
def empty_embedding_cache():
    retriever_mod._embed_query.cache_clear()
    yield
    retriever_mod._embed_query.cache_clear()


def test_the_same_text_is_embedded_once(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[list[str]] = []

    def embed(texts: list[str], params: Any, **_: Any) -> list[list[float]]:
        sent.append(texts)
        return [[1.0, 0.0]]

    monkeypatch.setattr(retriever_mod, "embed_texts", embed)
    retriever = retriever_mod.Retriever(_FakeVDB(), EmbedParams("m", "http://unused"))
    for text in ("orders", "orders", "customers"):
        retriever.query(text)
    assert sent == [["orders"], ["customers"]]


def test_a_failed_embedding_is_not_remembered(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[str] = []

    def embed(texts: list[str], params: Any, **_: Any) -> list[list[float]]:
        attempts.append(texts[0])
        if len(attempts) == 1:
            raise RuntimeError("endpoint down")
        return [[1.0, 0.0]]

    monkeypatch.setattr(retriever_mod, "embed_texts", embed)
    retriever = retriever_mod.Retriever(_FakeVDB(), EmbedParams("m", "http://unused"))
    with pytest.raises(RuntimeError):
        retriever.query("orders")
    retriever.query("orders")
    assert attempts == ["orders", "orders"]
