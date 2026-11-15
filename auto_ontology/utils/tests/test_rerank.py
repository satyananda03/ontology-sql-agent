"""Tests for :func:`auto_ontology.utils.rerank.rerank_hits`.

The request shape is pinned here: a request in the wrong shape is rejected by
the gateway and every bridge-table owner falls back to the first Term without
anyone noticing.
"""

import json
from typing import Any, Callable

import httpx
import pytest

from auto_ontology.utils import rerank
from auto_ontology.utils.rerank import rerank_hits

Server = Callable[..., list[httpx.Request]]

_HITS = [
    {"id": "a", "text": "apples"},
    {"id": "b", "text": "bananas"},
    {"id": "c", "text": "cherries"},
]


@pytest.fixture
def server(
    monkeypatch: pytest.MonkeyPatch,
) -> Server:
    """Answer the next POST with *body*; returns the requests seen."""

    def _install(body: dict[str, Any], status: int = 200) -> list[httpx.Request]:
        seen: list[httpx.Request] = []

        def _post(url: str, **kwargs: Any) -> httpx.Response:
            request = httpx.Request(
                "POST", url, json=kwargs["json"], headers=kwargs["headers"]
            )
            seen.append(request)
            assert kwargs["timeout"] == rerank._TIMEOUT_S
            return httpx.Response(status, json=body, request=request)

        monkeypatch.setattr(rerank.httpx, "post", _post)
        return seen

    return _install


def test_the_rerank_schema(server: Server) -> None:
    seen = server(
        {
            "results": [
                {"index": 2, "relevance_score": 0.9},
                {"index": 0, "relevance_score": 0.1},
            ]
        }
    )

    ranked = rerank_hits(
        "fruit",
        _HITS,
        rerank_invoke_url="https://inference.example/v1/rerank",
        model_name="m",
        api_key="sk-x",
    )

    [request] = seen
    assert str(request.url) == "https://inference.example/v1/rerank"
    assert request.headers["authorization"] == "Bearer sk-x"
    assert json.loads(request.content) == {
        "model": "m",
        "query": "fruit",
        "documents": ["apples", "bananas", "cherries"],
        "top_n": 3,
    }
    # b was not returned, so it ranks last rather than disappearing.
    assert [(h["id"], h["_rerank_score"]) for h in ranked] == [
        ("c", 0.9),
        ("a", 0.1),
        ("b", float("-inf")),
    ]


def test_top_n_keeps_only_the_best(server: Server) -> None:
    server(
        {
            "results": [
                {"index": 1, "relevance_score": 4.0},
                {"index": 0, "relevance_score": -2.0},
            ]
        }
    )

    ranked = rerank_hits(
        "fruit",
        _HITS[:2],
        rerank_invoke_url="https://gateway.example/v1/rerank/",
        model_name="m",
        top_n=1,
    )

    assert [h["id"] for h in ranked] == ["b"]


def test_the_binding_supplies_the_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RERANK_BINDING_HOST", "https://gateway.example/v1/rerank")
    monkeypatch.setenv("RERANK_MODEL", "rerank-model")
    monkeypatch.setenv("RERANK_BINDING_API_KEY", "sk-rerank")

    assert rerank.get_rerank_kwargs() == {
        "rerank_invoke_url": "https://gateway.example/v1/rerank",
        "model_name": "rerank-model",
        "api_key": "sk-rerank",
    }


def test_an_endpoint_error_reaches_the_caller(server: Server) -> None:
    server({"error": "nope"}, status=500)
    with pytest.raises(httpx.HTTPStatusError):
        rerank_hits("q", _HITS, rerank_invoke_url="http://x/rerank", model_name="m")


def test_no_hits_makes_no_request(server: Server) -> None:
    seen = server({})
    assert (
        rerank_hits("q", [], rerank_invoke_url="http://x/rerank", model_name="m") == []
    )
    assert seen == []
