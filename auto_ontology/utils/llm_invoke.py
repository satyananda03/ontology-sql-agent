"""How auto_ontology calls the LLM: one structured request, retried.

Callers build a client with :func:`auto_ontology.utils.llm_client.get_llm_client`
and pass it here with their messages and the schema they want back. This module
does not know how the client was built; it owns what happens around the request:

* the retry policy for transient errors and for replies that do not validate,
* message preparation for models with stricter rules (Claude),
* how the schema is asked for (``response_format``, or tool calling for Claude),
* the in-flight bound, taken around every request.
"""

import logging
import random
import time
from typing import Any, Type, TypeVar

from langchain_core.exceptions import OutputParserException
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.outputs import Generation
from langchain_core.runnables import Runnable
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from auto_ontology.utils.llm_inflight import inflight_guard

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class StrictLLMOutputModel(BaseModel):
    """Base for LLM structured-output schemas.

    Forbids genuine hallucinated fields (``extra="forbid"``) but first strips any
    key starting with ``$`` — some models leak tool-calling metadata (e.g. a stray
    ``$FUNCTION_NAME`` field echoing the tool name) into the arguments payload,
    which would otherwise fail validation and burn all retry attempts even though
    the real data is fine. Opt a schema into this by inheriting from it instead of
    ``BaseModel``.
    """

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def _strip_provider_artifact_keys(cls, data):
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if not k.startswith("$")}
        return data


# ---------------------------------------------------------------------------
# Retry policy
# ---------------------------------------------------------------------------

RETRY_MAX_ATTEMPTS = 3

# Substrings that indicate a transient, retryable server condition.
_RETRYABLE_TOKENS = (
    "429",
    "Too Many Requests",
    "503",
    "ResourceExhausted",
    "Service Unavailable",
    "timed out",
    "APITimeoutError",
    "ReadTimeout",
    # Azure / LiteLLM connection failures
    "Connection error",
    "APIConnectionError",
    "AzureException",
    "InternalServerError",
    "litellm",
)

# Exception *type* names that are always transient/retryable regardless of
# message text. Needed because str(exception) for openai's typed errors
# (e.g. openai.InternalServerError) returns only the message body — never
# the class name — so a message like "upstream connect error or
# disconnect/reset before headers... Connection refused" silently fails
# every _RETRYABLE_TOKENS substring check above even though
# "InternalServerError" is right there in the token list. Matching on
# type(e).__name__ catches these regardless of how the provider phrases
# the underlying message.
_RETRYABLE_EXCEPTION_TYPES = frozenset(
    {
        "InternalServerError",
        "APIConnectionError",
        "APITimeoutError",
        "RateLimitError",
        "ServiceUnavailableError",
    }
)


def _is_retryable(e: Exception) -> bool:
    """Whether *e* signals a transient, retryable server condition."""
    return any(tok in str(e) for tok in _RETRYABLE_TOKENS) or (
        type(e).__name__ in _RETRYABLE_EXCEPTION_TYPES
    )


# ---------------------------------------------------------------------------
# Message preparation
# ---------------------------------------------------------------------------


def _ensure_non_system_message(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Guarantee at least one non-system message.

    Anthropic/Bedrock (via the OpenAI-compatible gateway) reject requests that
    contain only system messages with "bedrock requires at least one non-system
    message". Many agents build a single ``SystemMessage`` prompt, so when no
    user/assistant message is present we promote the last system message to a
    ``HumanMessage`` (its content is the actual instruction). No-op when a
    non-system message already exists.
    """
    if not messages or any(not isinstance(m, SystemMessage) for m in messages):
        return messages
    converted = list(messages)
    converted[-1] = HumanMessage(content=converted[-1].content)
    return converted


def _model_name(llm: BaseChatModel) -> str:
    """The model *llm* serves, whichever attribute its client class keeps it in."""
    return str(getattr(llm, "model_name", "") or getattr(llm, "model", "") or "")


def _is_claude(llm: BaseChatModel) -> bool:
    """True when *llm* serves an Anthropic/Claude model, matched by name."""
    lowered = _model_name(llm).lower()
    return "anthropic" in lowered or "claude" in lowered


def _system_messages_first(
    llm: BaseChatModel, messages: list[BaseMessage]
) -> list[BaseMessage]:
    """Move every system message ahead of the conversation for Claude models.

    Claude takes a single system prompt ahead of the conversation, but agents
    interleave them: ``sql_from_semantic`` sends system, user, system, system,
    user, and a validation retry appends a system message after the user turn.
    On the inference-api gateway, ``azure/anthropic/*`` rejects every request
    with a system message after a user message, because the gateway attaches
    prompt-cache markers in an order Anthropic refuses::

        messages.1.content.0.cache_control.ttl: a ttl='1h' cache_control block
        must not come after a ttl='5m' cache_control block.

    Measured against the live endpoint: system, user, system, user fails every
    time on ``azure/anthropic/claude-opus-5-5`` and succeeds once the system
    messages lead. Relative order within each group is kept. Other models keep
    the order they were given.
    """
    if not _is_claude(llm):
        return messages
    system = [m for m in messages if isinstance(m, SystemMessage)]
    rest = [m for m in messages if not isinstance(m, SystemMessage)]
    return system + rest


def _structured_output_kwargs(llm: BaseChatModel) -> dict:
    """Pick the ``with_structured_output`` method for *llm*.

    Anthropic/Claude models served through the OpenAI-compatible gateway (e.g.
    ``aws/anthropic/bedrock-claude-opus-4-8``) reject the default json_schema /
    ``response_format`` path ("output_config.format: Extra inputs are not
    permitted"), but they support tool calling — so force ``function_calling``
    for them. Everything else keeps langchain's default (json_schema for
    OpenAI), which is preferred where supported.

    ``tool_choice=None`` suppresses the tool-choice langchain would otherwise set.
    Bedrock behind LiteLLM rejects the request when one is present, because the gateway
    both maps it into ``toolConfig.toolChoice`` and forwards the original
    ``tool_choice.type``::

        The additional field tool_choice/type conflicts with the existing field
        toolConfig.toolChoice.tool. Remove tool_choice/type and try again.

    Measured against the live endpoint: every explicit value ("auto", "any",
    "required", and langchain's default of naming the tool) hits that conflict, and only
    omitting it succeeds. The model still calls the tool without being forced to, and
    the caller retries if it ever answers without one.
    """
    if _is_claude(llm):
        return {"method": "function_calling", "tool_choice": None}
    return {}


# ---------------------------------------------------------------------------
# Structured output
# ---------------------------------------------------------------------------


class _ParseOrNone(PydanticOutputParser[Any]):
    """Parse the reply into the schema, or ``None`` when it does not fit.

    ``None`` is the signal ``safe_invoke_with_structured_output`` retries on.
    """

    def parse_result(self, result: list[Generation], *, partial: bool = False) -> Any:
        try:
            return super().parse_result(result, partial=partial)
        except OutputParserException:
            return None


def _structured_llm(llm: BaseChatModel, schema: Type[T]) -> Runnable:
    """*llm* bound to answer with *schema*.

    The gateway is asked with the OpenAI ``response_format`` (a strict JSON
    schema), and the reply is parsed here so a reply that does not fit comes
    back as ``None``. Claude rejects ``response_format`` and is asked through
    tool calling instead, see :func:`_structured_output_kwargs`.
    """
    if _is_claude(llm):
        return llm.with_structured_output(schema, **_structured_output_kwargs(llm))
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": schema.__name__,
            "schema": schema.model_json_schema(),
            "strict": True,
        },
    }
    return llm.bind(response_format=response_format) | _ParseOrNone(
        pydantic_object=schema
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def safe_invoke_with_structured_output(
    llm: BaseChatModel,
    messages: list[BaseMessage],
    schema: Type[T],
) -> T:
    """LLM structured call with retry."""
    current_messages = _ensure_non_system_message(messages.copy())
    schema_name = getattr(schema, "__name__", str(schema))

    for attempt in range(RETRY_MAX_ATTEMPTS):
        try:
            model_llm = _structured_llm(llm, schema)
            with inflight_guard():
                result = model_llm.invoke(_system_messages_first(llm, current_messages))
        except ValidationError as e:
            if attempt < RETRY_MAX_ATTEMPTS - 1:
                if attempt == 0:
                    # First retry: append the error so the model can self-correct.
                    current_messages.append(
                        SystemMessage(
                            content=(
                                "Your previous output did not validate. "
                                f"Validation errors:\n{str(e)}\n"
                                "Please return a **fully valid** object that satisfies the schema. "
                                "Do not omit required fields. Do not include extra keys."
                            )
                        )
                    )
                else:
                    # Subsequent retries: the accumulated error context didn't help —
                    # reset to fresh messages to avoid compounding the confusion.
                    logger.warning(
                        "Structured output still failing after error-context retry "
                        "(attempt %d/%d) for %s — resetting to fresh messages",
                        attempt + 1,
                        RETRY_MAX_ATTEMPTS,
                        schema_name,
                    )
                    current_messages = _ensure_non_system_message(messages.copy())
                continue
            else:
                logger.error(
                    f"Validation failed after {RETRY_MAX_ATTEMPTS} attempts for {schema_name}"
                )
                raise
        except Exception as e:
            is_retryable = _is_retryable(e)
            if is_retryable and attempt < RETRY_MAX_ATTEMPTS - 1:
                wait = 2 ** (attempt + 1) + random.uniform(0, 1)
                logger.warning(
                    "Retryable LLM error (endpoint saturated/rate-limited) on attempt "
                    "%d/%d for %s — retrying in %.1fs",
                    attempt + 1,
                    RETRY_MAX_ATTEMPTS,
                    schema_name,
                    wait,
                )
                time.sleep(wait)
                continue
            logger.error(
                f"Unexpected error on attempt {attempt + 1}/{RETRY_MAX_ATTEMPTS} for {schema_name}: "
                f"{type(e).__name__}: {e}",
                exc_info=True,
            )
            raise

        if result is None:
            logger.warning(
                "LLM returned None for %s on attempt %d/%d — retrying.",
                schema_name,
                attempt + 1,
                RETRY_MAX_ATTEMPTS,
            )
            if attempt < RETRY_MAX_ATTEMPTS - 1:
                wait = 2 ** (attempt + 1) + random.uniform(0, 1)
                time.sleep(wait)
            continue
        if isinstance(result, schema):
            return result
        return schema.model_validate(result)


def invoke_with_structured_output(
    llm: BaseChatModel,
    messages: list[BaseMessage],
    schema: Type[T],
) -> T | None:
    """:func:`safe_invoke_with_structured_output` that returns None on failure."""
    schema_name = getattr(schema, "__name__", str(schema))
    started = time.perf_counter()
    try:
        return safe_invoke_with_structured_output(llm, messages, schema)
    except Exception as e:
        logger.error(
            f"invoke_with_structured_output failed for {schema_name} after {RETRY_MAX_ATTEMPTS} attempts: "
            f"{type(e).__name__}: {e}",
            exc_info=True,
        )
        return None
    finally:
        # Wall time including retries: what the caller waited.
        logger.info("[TIMING] llm %s %.2fs", schema_name, time.perf_counter() - started)
