"""Rerank candidate hits against a query with the gateway's ``/rerank`` route.

``RERANK_BINDING_HOST`` is the full URL of that route. The request is
``{"model", "query", "documents", "top_n"}`` and each document is scored by
``results[].relevance_score``.
"""

from typing import Any

import httpx

from auto_ontology.utils.model_config import binding

_TIMEOUT_S = 30.0


def get_rerank_kwargs() -> dict[str, str]:
    """Keyword args for :func:`rerank_hits`, from the ``RERANK`` binding."""
    rerank = binding("RERANK")
    return {
        "rerank_invoke_url": rerank.host,
        "model_name": rerank.model,
        "api_key": rerank.api_key,
    }


def _scores(
    query: str,
    documents: list[str],
    *,
    url: str,
    model_name: str,
    api_key: str,
    timeout_s: float,
) -> list[float]:
    """One score per document, higher is better; ``-inf`` for any not returned."""
    payload: dict[str, Any] = {
        "model": model_name,
        "query": query,
        "documents": documents,
        "top_n": len(documents),
    }
    headers = {"accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = httpx.post(url, json=payload, headers=headers, timeout=timeout_s)
    response.raise_for_status()
    data = response.json()

    items = data.get("results") if isinstance(data, dict) else None
    scores = [float("-inf")] * len(documents)
    for item in items if isinstance(items, list) else []:
        try:
            index, score = int(item["index"]), float(item["relevance_score"])
        except (KeyError, TypeError, ValueError):
            continue
        if 0 <= index < len(scores):
            scores[index] = score
    return scores


def rerank_hits(
    query: str,
    hits: list[dict[str, Any]],
    *,
    rerank_invoke_url: str,
    model_name: str,
    api_key: str = "",
    top_n: int | None = None,
    text_key: str = "text",
    timeout_s: float = _TIMEOUT_S,
) -> list[dict[str, Any]]:
    """*hits* sorted by relevance to *query*, best first, each with ``_rerank_score``.

    A hit that already carries ``_rerank_score`` keeps it. Ties keep their
    input order. Raises on an endpoint error or after *timeout_s*; the caller
    picks the fallback.
    """
    if not hits:
        return hits
    scores = _scores(
        query,
        [str(hit.get(text_key) or "") for hit in hits],
        url=rerank_invoke_url.rstrip("/"),
        model_name=model_name,
        api_key=api_key,
        timeout_s=timeout_s,
    )
    ranked = sorted(
        ({"_rerank_score": score, **hit} for hit, score in zip(hits, scores)),
        key=lambda hit: hit["_rerank_score"],
        reverse=True,
    )
    return ranked[:top_n] if top_n is not None else ranked
