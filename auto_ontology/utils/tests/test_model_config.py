"""The one place model endpoints are read from the environment."""

import pytest

from auto_ontology.utils.model_config import binding


def test_a_binding_is_its_three_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODEL", "chat-model")
    monkeypatch.setenv("LLM_BINDING_HOST", "https://gateway.example/v1")
    monkeypatch.setenv("LLM_BINDING_API_KEY", "sk-llm")
    monkeypatch.setenv("EMBEDDING_MODEL", "embed-model")

    llm = binding("LLM")

    assert (llm.model, llm.host, llm.api_key) == (
        "chat-model",
        "https://gateway.example/v1",
        "sk-llm",
    )
    # Each binding reads its own names: nothing is shared between them.
    assert binding("EMBEDDING").model == "embed-model"
    assert binding("RERANK").model == ""


def test_the_key_stays_out_of_the_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BINDING_API_KEY", "sk-secret")

    assert "sk-secret" not in repr(binding("LLM"))


@pytest.mark.parametrize(
    "legacy",
    [
        "REASONING_API_KEY",
        "NON_REASONING_API_KEY",
        "EMBED_API_KEY",
        "DEFAULT_MODELS_API_KEY",
        "NVIDIA_API_KEY",
    ],
)
def test_an_unset_binding_is_empty_whatever_older_names_say(
    monkeypatch: pytest.MonkeyPatch, legacy: str
) -> None:
    """No default endpoint and no older name: a missing setting must not resolve."""
    for name in ("LLM", "EMBEDDING", "RERANK"):
        for suffix in ("MODEL", "BINDING_HOST", "BINDING_API_KEY"):
            monkeypatch.delenv(f"{name}_{suffix}", raising=False)
    monkeypatch.setenv(legacy, "nvapi-old")

    for name in ("LLM", "EMBEDDING", "RERANK"):
        unset = binding(name)  # type: ignore[arg-type]
        assert (unset.model, unset.host, unset.api_key) == ("", "", "")
