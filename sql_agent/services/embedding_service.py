"""Klien embedding teks: ``RetryingEmbeddings`` dan factory ``get_embeddings``."""

import functools
from functools import lru_cache
from langchain_openai import OpenAIEmbeddings
from sql_agent.core.config import settings
from sql_agent.services.retry_service import per_instance


def _by_index(response, count: int) -> list[list[float]]:
    """Vektor satu respons, diurutkan menurut ``index``-nya, tepat satu per input.

    Gateway bisa mengacak urutan ``data`` di bawah beban paralel (Titan di belakang LiteLLM), jadi posisi tidak
    bisa dipercaya. Vektor yang hilang atau ganda ditolak: kalau lolos, teks dipasangkan dengan vektor teks lain
    tanpa ada yang menyadarinya.
    """
    data = sorted(response.data, key=lambda item: item.index)
    if [item.index for item in data] != list(range(count)):
        raise RuntimeError(
            f"Embedding endpoint returned {len(data)} vector(s) for {count} input(s)."
        )
    return [list(item.embedding) for item in data]


def embed_by_index_sync(create, texts: list[str], chunk_size: int) -> list[list[float]]:
    vectors: list[list[float]] = []
    for start in range(0, len(texts), chunk_size):
        chunk = texts[start : start + chunk_size]
        vectors += _by_index(create(input=chunk), len(chunk))
    return vectors


async def embed_by_index(
    create, texts: list[str], chunk_size: int
) -> list[list[float]]:
    vectors: list[list[float]] = []
    for start in range(0, len(texts), chunk_size):
        chunk = texts[start : start + chunk_size]
        vectors += _by_index(await create(input=chunk), len(chunk))
    return vectors


class RetryingEmbeddings(OpenAIEmbeddings):
    """Vektor dipasangkan lewat ``index``, bukan posisi (lihat :func:`_by_index`)."""

    retry_attempts: int = 1

    @per_instance
    def embed_documents(self, texts, chunk_size=None, **kwargs):
        self._ensure_sync_client_available()
        create = functools.partial(
            self.client.create, **self._invocation_params, **kwargs
        )
        return embed_by_index_sync(create, texts, chunk_size or self.chunk_size)

    @per_instance
    async def aembed_documents(self, texts, chunk_size=None, **kwargs):
        create = functools.partial(
            self.async_client.create, **self._invocation_params, **kwargs
        )
        return await embed_by_index(create, texts, chunk_size or self.chunk_size)

    @per_instance
    def embed_query(self, *args, **kwargs):
        return super().embed_query(*args, **kwargs)

    @per_instance
    async def aembed_query(self, *args, **kwargs):
        return await super().aembed_query(*args, **kwargs)


@lru_cache(maxsize=5)
def get_embeddings(
    model_id: str | None = None,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    timeout: float | None = None,
    max_retries: int | None = None,
) -> RetryingEmbeddings:
    """Model embedding teks; binding default ``EMBEDDING_BINDING_*``."""
    return RetryingEmbeddings(
        model=model_id or settings.embedding_model,
        base_url=base_url or settings.embedding_binding_host,
        api_key=api_key or settings.embedding_binding_api_key,
        timeout=timeout or settings.embedding_timeout,
        max_retries=0,
        retry_attempts=settings.max_retries if max_retries is None else max_retries,
        model_kwargs={"encoding_format": "float"},
        check_embedding_ctx_length=False,
    )
