"""Klien rerank: factory ``get_reranker`` (HTTP langsung ke ``RERANK_BINDING_HOST``)."""

import asyncio

import httpx

from sql_agent.core.config import settings
from sql_agent.services.retry_service import with_retry

MAX_RERANK_CHARS = (
    4000  # per dokumen; provider menolak payload rerank yang terlalu panjang
)
#: Default httpx 5 dtk: jeda antar-rerank dalam satu giliran chat (menunggu LLM) biasanya lebih lama dari itu.
KEEPALIVE_S = 30.0

_client: httpx.AsyncClient | None = None
_client_loop: asyncio.AbstractEventLoop | None = None


def _get_client() -> httpx.AsyncClient:
    """Satu klien per event loop, supaya koneksi TLS dipakai ulang. Koneksinya terikat ke loop pembuatnya:
    tanpa cek ini, ``asyncio.run`` kedua di skrip mewarisi koneksi mati dan rerank diam-diam jatuh ke urutan asli."""
    global _client, _client_loop
    loop = asyncio.get_running_loop()
    if _client is None or _client_loop is not loop:
        _client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
                keepalive_expiry=KEEPALIVE_S,
            )
        )
        _client_loop = loop
    return _client


async def close_client() -> None:
    global _client, _client_loop
    if _client is not None:
        await _client.aclose()
        _client = _client_loop = None


def get_reranker(
    model_id: str | None = None,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    timeout: float | None = None,
    max_retries: int | None = None,
):
    """``async rerank(query, documents, top_n=None) -> [{"index", "relevance_score", ...}]``.

    ``base_url`` adalah URL endpoint rerank utuh (``RERANK_BINDING_HOST``). Kegagalan dilempar;
    pemanggil yang memilih jalur cadangannya (urutan asli).
    """
    model_id, url = (
        model_id or settings.rerank_model,
        base_url or settings.rerank_binding_host,
    )
    key, timeout = (
        api_key or settings.rerank_binding_api_key,
        timeout or settings.rerank_timeout,
    )

    @with_retry(lambda *_: settings.max_retries if max_retries is None else max_retries)
    async def post(payload: dict) -> dict:
        response = await _get_client().post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {key}"},
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    async def rerank(
        query: str, documents: list[str], top_n: int | None = None
    ) -> list[dict]:
        if not documents:
            return []
        top_n = (
            min(top_n, len(documents)) if top_n else len(documents)
        )  # Amazon Rerank menolak top_n > jumlah dokumen
        data = await post(
            {
                "model": model_id,
                "query": query,
                "documents": [d[:MAX_RERANK_CHARS] for d in documents],
                "top_n": top_n,
            }
        )
        # Amazon Rerank menamai skornya ``relevanceScore``.
        return [
            {
                "index": r["index"],
                "relevance_score": r.get(
                    "relevance_score", r.get("relevanceScore", 0.0)
                ),
            }
            for r in data.get("results", [])
        ]

    return rerank
