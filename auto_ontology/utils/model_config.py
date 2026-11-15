"""Model endpoints of auto_ontology: the one place their env vars are read.

Every model is reached through an OpenAI-compatible gateway (LiteLLM), and each
binding is three env vars, the same ones ``sql_agent/core/config.py`` reads::

    LLM_MODEL        LLM_BINDING_HOST        LLM_BINDING_API_KEY
    EMBEDDING_MODEL  EMBEDDING_BINDING_HOST  EMBEDDING_BINDING_API_KEY
    RERANK_MODEL     RERANK_BINDING_HOST     RERANK_BINDING_API_KEY

Only the client modules call :func:`binding` -- ``llm_client``, ``embedding``
and ``rerank``. Everything else asks those modules for a ready client or its
parameters, so a new setting has one place to be read from.

An unset variable is an empty string. There is no default endpoint: a missing
setting fails where it is used instead of quietly calling somewhere else.
"""

import os
from dataclasses import dataclass, field
from typing import Literal

BindingName = Literal["LLM", "EMBEDDING", "RERANK"]


@dataclass(frozen=True)
class Binding:
    """One model endpoint. The key is kept out of ``repr`` and so out of logs."""

    model: str
    host: str
    api_key: str = field(repr=False)


def binding(name: BindingName) -> Binding:
    """The *name* binding as the environment currently sets it."""
    return Binding(
        model=os.environ.get(f"{name}_MODEL", ""),
        host=os.environ.get(f"{name}_BINDING_HOST", ""),
        api_key=os.environ.get(f"{name}_BINDING_API_KEY", ""),
    )
