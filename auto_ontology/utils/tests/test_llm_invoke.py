"""Tests for how a structured LLM call is made: preparation, format, retries."""

from typing import Any
from unittest.mock import MagicMock

import httpx
import openai
import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

from auto_ontology.utils import llm_invoke
from auto_ontology.utils.llm_invoke import (
    _structured_output_kwargs,
    _system_messages_first,
)


@pytest.fixture(autouse=True)
def _no_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Retries wait seconds between attempts; the tests only count them."""
    monkeypatch.setattr(llm_invoke.time, "sleep", lambda _seconds: None)


class _Model:
    """Stand-in exposing the model name the way langchain clients do."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name


def test_claude_uses_function_calling_without_a_tool_choice() -> None:
    """Bedrock behind LiteLLM rejects any explicit tool choice.

    The gateway maps tool_choice into ``toolConfig.toolChoice`` *and* forwards the
    original ``tool_choice.type``, and Bedrock refuses the pair:

        The additional field tool_choice/type conflicts with the existing field
        toolConfig.toolChoice.tool.

    Measured against the live endpoint: "auto", "any", "required" and langchain's
    default (naming the tool) all hit it; only omitting the choice succeeds.
    """
    kwargs = _structured_output_kwargs(_Model("aws/anthropic/bedrock-claude-opus-4-8"))

    assert kwargs == {"method": "function_calling", "tool_choice": None}


def test_claude_is_matched_on_either_vendor_or_family_name() -> None:
    for name in (
        "aws/anthropic/bedrock-claude-opus-4-8",
        "claude-3-5-sonnet",
        "ANTHROPIC/Claude",
    ):
        assert _structured_output_kwargs(_Model(name))["method"] == "function_calling"


def test_other_models_keep_the_langchain_default() -> None:
    """json_schema is preferred where supported, so nothing is forced for them."""
    for name in ("nvidia/nemotron-3.5-lightning-30b-a3b", "gpt-4o", ""):
        assert _structured_output_kwargs(_Model(name)) == {}


def test_a_client_exposing_model_instead_of_model_name_still_matches() -> None:
    """Some langchain clients expose `model` rather than `model_name`."""

    class _AltModel:
        model: Any = "aws/anthropic/bedrock-claude-opus-4-8"

    assert _structured_output_kwargs(_AltModel())["tool_choice"] is None


def _interleaved() -> list[BaseMessage]:
    """The shape sql_from_semantic sends: system, user, system, system, user."""
    return [
        SystemMessage(content="role"),
        HumanMessage(content="question"),
        SystemMessage(content="evidence"),
        SystemMessage(content="anchors"),
        HumanMessage(content="prompt"),
    ]


def test_claude_gets_its_system_messages_ahead_of_the_conversation() -> None:
    """azure/anthropic/* on the gateway 400s on a system message after a user one."""
    ordered = _system_messages_first(
        _Model("azure/anthropic/claude-opus-5-5"), _interleaved()
    )

    assert [m.content for m in ordered] == [
        "role",
        "evidence",
        "anchors",
        "question",
        "prompt",
    ]


def test_other_models_keep_their_message_order() -> None:
    messages = _interleaved()

    assert (
        _system_messages_first(
            _Model("nvidia/nemotron-3.5-lightning-30b-a3b"), messages
        )
        == messages
    )


class _SystemCheckModel(BaseModel):
    answer: str


def test_validation_retry_note_reaches_claude_ahead_of_the_conversation() -> None:
    """The retry appends a system message after the user turn; it must not stay there."""
    sent: list[list[BaseMessage]] = []

    class _Structured:
        def invoke(self, messages: list[BaseMessage]) -> _SystemCheckModel:
            sent.append(messages)
            if len(sent) == 1:
                _SystemCheckModel.model_validate({})
            return _SystemCheckModel(answer="ok")

    class _Claude(_Model):
        def with_structured_output(self, *_args: Any, **_kwargs: Any) -> _Structured:
            return _Structured()

    llm_invoke.safe_invoke_with_structured_output(
        _Claude("azure/anthropic/claude-opus-5-5"),  # type: ignore[arg-type]
        [SystemMessage(content="role"), HumanMessage(content="question")],
        _SystemCheckModel,
    )

    roles = [m.type for m in sent[1]]
    assert roles == ["system", "system", "human"]


class _Answer(BaseModel):
    answer: str


class _RecordingChat(FakeListChatModel):
    """A chat model that replays canned replies and keeps each request's kwargs."""

    seen: list[dict[str, Any]] = []

    def _call(self, *args: Any, **kwargs: Any) -> str:
        self.seen.append(kwargs)
        return super()._call(*args, **kwargs)


def test_the_gateway_is_asked_once_with_response_format() -> None:
    llm = _RecordingChat(responses=['{"answer": "ok"}'])

    result = llm_invoke.safe_invoke_with_structured_output(
        llm, [HumanMessage(content="question")], _Answer
    )

    assert result == _Answer(answer="ok")
    assert len(llm.seen) == 1
    assert llm.seen[0]["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "_Answer",
            "schema": _Answer.model_json_schema(),
            "strict": True,
        },
    }


def test_a_reply_that_does_not_fit_the_schema_is_none() -> None:
    # None is what the retry loop acts on; an exception would skip the retries.
    llm = _RecordingChat(responses=["The answer is ok."])

    assert llm_invoke._structured_llm(llm, _Answer).invoke("question") is None


def test_claude_keeps_the_librarys_own_structured_output() -> None:
    """Claude rejects response_format, so it is asked through tool calling."""
    llm = MagicMock(model_name="claude-3-5-sonnet")

    llm_invoke._structured_llm(llm, _Answer)

    llm.with_structured_output.assert_called_once()
    llm.bind.assert_not_called()


@pytest.mark.parametrize(
    "model", ["moonshotai.kimi-k2.5", "openai/gpt-5", "meta/llama-3.1-70b-instruct"]
)
def test_every_other_model_is_asked_with_response_format(model: str) -> None:
    """One path behind the gateway, whatever the model is called."""
    llm = MagicMock(model_name=model)

    llm_invoke._structured_llm(llm, _Answer)

    llm.with_structured_output.assert_not_called()
    llm.bind.assert_called_once()


def _timeout() -> openai.APITimeoutError:
    return openai.APITimeoutError(httpx.Request("POST", "https://gateway.example"))


class _FlakyChat(FakeListChatModel):
    """Raises each queued error once, then answers from ``responses``."""

    errors: list[Exception] = []
    calls: int = 0

    def _call(self, *args: Any, **kwargs: Any) -> str:
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return super()._call(*args, **kwargs)


def test_a_timed_out_request_is_retried() -> None:
    """The client raises APITimeoutError; it is transient, like a 429 or a 503."""
    llm = _FlakyChat(responses=['{"answer": "ok"}'], errors=[_timeout()])

    result = llm_invoke.safe_invoke_with_structured_output(
        llm, [HumanMessage(content="question")], _Answer
    )

    assert result == _Answer(answer="ok")
    assert llm.calls == 2


def test_a_call_that_keeps_failing_is_none_for_the_caller() -> None:
    """Agents have their own fallback for a missing answer; an exception is not one."""
    errors = [_timeout() for _ in range(llm_invoke.RETRY_MAX_ATTEMPTS)]
    llm = _FlakyChat(responses=['{"answer": "ok"}'], errors=errors)

    result = llm_invoke.invoke_with_structured_output(
        llm, [HumanMessage(content="question")], _Answer
    )

    assert result is None
    assert llm.calls == llm_invoke.RETRY_MAX_ATTEMPTS


def test_a_request_the_gateway_refuses_is_not_retried() -> None:
    """A wrong request stays wrong: retrying would only spend the attempts."""
    llm = _FlakyChat(responses=['{"answer": "ok"}'], errors=[ValueError("bad request")])

    with pytest.raises(ValueError, match="bad request"):
        llm_invoke.safe_invoke_with_structured_output(
            llm, [HumanMessage(content="question")], _Answer
        )

    assert llm.calls == 1
