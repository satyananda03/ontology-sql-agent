"""With a rerank pool the reranker picks which hits to keep; without one nothing changes."""

from typing import Any

import pytest

from auto_ontology.retrieval.data_access import semantic_search
from auto_ontology.retrieval.data_access.semantic_search import search_semantic_index

LABEL = "ColumnAttribute"


class FakeRetriever:
    """Returns hits best distance first, as the vector store does."""

    def __init__(self, names: list[str]) -> None:
        self.names = names
        self.requested: list[int] = []

    def query(self, text: str, top_k: int, vdb_kwargs: Any) -> list[dict]:
        self.requested.append(top_k)
        return [
            {
                "text": name,
                "metadata": {"id": name, "label": LABEL},
                "_distance": 0.1 * position,
            }
            for position, name in enumerate(self.names[:top_k], 1)
        ]


def _rerank_preferring(*favourites: str):
    def rerank(query: str, hits: list[dict], *, top_n: int, **_: Any) -> list[dict]:
        ranked = sorted(hits, key=lambda hit: hit["text"] not in favourites)
        return ranked[:top_n]

    return rerank


def _search(retriever: FakeRetriever, **kwargs: Any) -> list[dict]:
    return search_semantic_index(
        retriever, "peserta", label_filter=[LABEL], per_label_k=2, **kwargs
    )


def test_reranker_chooses_from_the_pool_and_distance_stays_the_score(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(semantic_search, "rerank_hits", _rerank_preferring("d", "c"))
    retriever = FakeRetriever(["a", "b", "c", "d", "e"])

    rows = _search(retriever, rerank_pool=4)

    assert retriever.requested == [4]
    assert {row["id"] for row in rows} == {"c", "d"}
    assert {row["id"]: row["score"] for row in rows} == pytest.approx(
        {"c": 0.3, "d": 0.4}
    )


def test_reranker_failure_keeps_the_vector_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken(*_: Any, **__: Any) -> list[dict]:
        raise RuntimeError("rerank endpoint down")

    monkeypatch.setattr(semantic_search, "rerank_hits", broken)

    rows = _search(FakeRetriever(["a", "b", "c", "d"]), rerank_pool=4)

    assert [row["id"] for row in rows] == ["a", "b"]


def test_no_pool_asks_for_exactly_k_and_never_reranks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected(*_: Any, **__: Any) -> list[dict]:
        raise AssertionError("reranker must not run without a pool")

    monkeypatch.setattr(semantic_search, "rerank_hits", unexpected)
    retriever = FakeRetriever(["a", "b", "c"])

    rows = _search(retriever)

    assert retriever.requested == [2]
    assert [row["id"] for row in rows] == ["a", "b"]


def test_a_pool_no_larger_than_k_skips_the_reranker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected(*_: Any, **__: Any) -> list[dict]:
        raise AssertionError("nothing to choose between")

    monkeypatch.setattr(semantic_search, "rerank_hits", unexpected)

    rows = _search(FakeRetriever(["a", "b"]), rerank_pool=4)

    assert [row["id"] for row in rows] == ["a", "b"]
