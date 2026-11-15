"""The chat client auto_ontology reaches the LLM with.

One ``ChatOpenAI`` against the ``LLM`` binding, an OpenAI-compatible gateway
(LiteLLM). This module only builds the client: how a call is made -- retries,
structured output -- is :mod:`auto_ontology.utils.llm_invoke`'s business.
"""

import os

from langchain_openai import ChatOpenAI

from auto_ontology.utils.model_config import binding

# Seconds one request may take when the caller sets no timeout of its own.
LLM_INVOKE_TIMEOUT_S = int(os.environ.get("LLM_INVOKE_TIMEOUT_S", "120"))


def get_llm_client(
    *,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 8192,
    timeout: float | None = None,
) -> ChatOpenAI:
    """A chat client for the ``LLM`` binding; *model* overrides ``LLM_MODEL``.

    Raises ``EnvironmentError`` naming what is unset. Without that check an
    empty host would fall through to the client library's own default endpoint.
    """
    llm = binding("LLM")
    settings = {
        "LLM_MODEL": model or llm.model,
        "LLM_BINDING_HOST": llm.host,
        "LLM_BINDING_API_KEY": llm.api_key,
    }
    missing = [name for name, value in settings.items() if not value]
    if missing:
        raise EnvironmentError(f"{', '.join(missing)} is not set")

    return ChatOpenAI(
        model=settings["LLM_MODEL"],
        base_url=llm.host,
        api_key=llm.api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout or LLM_INVOKE_TIMEOUT_S,
        # llm_invoke owns the retries; a second layer here would multiply them.
        max_retries=0,
    )
