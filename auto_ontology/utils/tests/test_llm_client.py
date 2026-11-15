"""Tests for the chat client auto_ontology is given."""

import pytest
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from auto_ontology.utils.llm_client import LLM_INVOKE_TIMEOUT_S, get_llm_client


@pytest.fixture
def llm_binding(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODEL", "chat-model")
    monkeypatch.setenv("LLM_BINDING_HOST", "https://gateway.example/v1")
    monkeypatch.setenv("LLM_BINDING_API_KEY", "sk-test")


def test_the_client_is_chat_openai_on_the_llm_binding(llm_binding: None) -> None:
    llm = get_llm_client()

    assert isinstance(llm, ChatOpenAI)
    assert llm.model_name == "chat-model"
    assert llm.openai_api_base == "https://gateway.example/v1"
    assert llm.request_timeout == LLM_INVOKE_TIMEOUT_S
    # llm_invoke retries; the client must not retry underneath it.
    assert llm.max_retries == 0


def test_every_request_is_sent_at_temperature_zero(llm_binding: None) -> None:
    """Answers must be repeatable: the same question, the same SQL."""
    llm = get_llm_client(max_tokens=4096)

    payload = llm._get_request_payload([HumanMessage(content="question")])

    assert payload["temperature"] == 0.0
    assert payload["model"] == "chat-model"
    assert payload["max_completion_tokens"] == 4096
    assert payload["messages"] == [{"content": "question", "role": "user"}]


def test_a_caller_can_override_the_model_and_timeout(llm_binding: None) -> None:
    llm = get_llm_client(model="other-model", timeout=7.0)

    assert llm.model_name == "other-model"
    assert llm.request_timeout == 7.0


@pytest.mark.parametrize(
    "unset", ["LLM_MODEL", "LLM_BINDING_HOST", "LLM_BINDING_API_KEY"]
)
def test_a_missing_setting_is_named_instead_of_defaulted(
    llm_binding: None, monkeypatch: pytest.MonkeyPatch, unset: str
) -> None:
    """An empty host would otherwise fall through to the library's own endpoint."""
    monkeypatch.delenv(unset)

    with pytest.raises(EnvironmentError, match=unset):
        get_llm_client()
