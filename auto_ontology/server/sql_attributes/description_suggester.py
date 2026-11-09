"""On-demand LLM description suggestion for a single SqlAttribute."""

import logging
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from auto_ontology.dal.sql_attributes import (
    get_full_sql_attribute_by_id,
    set_sql_attribute_description_suggestion,
)
from auto_ontology.utils.llm_invoke import get_llm_client, invoke_with_structured_output
from auto_ontology.utils.prompt_loader import load_chat_prompt_template

logger = logging.getLogger(__name__)

_DESCRIPTION_SUGGESTION_MAX_CHARS = 500

_PROMPT = load_chat_prompt_template(
    Path(__file__).with_name("prompts.yaml"), "description_suggestion"
)


class _DescriptionSuggestionResponse(BaseModel):
    """LLM output: a suggested description for a SqlAttribute."""

    model_config = ConfigDict(extra="forbid")

    description: str = Field(
        max_length=_DESCRIPTION_SUGGESTION_MAX_CHARS,
        description="The suggested description for the SqlAttribute.",
    )


def _fit_description_suggestion(description: str) -> str:
    """Keep LLM output within the description-size budget before caching it.

    Also guards against a response that was itself cut off mid-sentence
    (e.g. by the LLM's ``max_tokens`` limit) by trimming back to the last
    complete sentence, even when the raw text is already within budget.
    """
    suggestion = " ".join(description.split())
    if len(suggestion) > _DESCRIPTION_SUGGESTION_MAX_CHARS:
        suggestion = suggestion[:_DESCRIPTION_SUGGESTION_MAX_CHARS].rstrip()

    if suggestion and suggestion[-1] in ".!?":
        return suggestion

    sentence_end = max(
        suggestion.rfind("."), suggestion.rfind("!"), suggestion.rfind("?")
    )
    if sentence_end > 0:
        return suggestion[: sentence_end + 1]
    return ""


def suggest_sql_attribute_description(attr_id: str) -> str | None:
    """Return a cached or freshly-generated description suggestion for a SqlAttribute.

    Reads the attribute's name, parent Term, and SQL from the store via
    :func:`get_full_sql_attribute_by_id`. When a ``description_suggestion``
    is already stored on the node, it is returned as-is (no LLM call).
    Otherwise the LLM drafts one, it is persisted on the node via
    :func:`set_sql_attribute_description_suggestion`, and returned.

    Returns ``None`` when the attribute doesn't exist or the LLM call
    fails/returns nothing usable — callers should treat that as "no
    suggestion available" rather than an error.
    """
    row = get_full_sql_attribute_by_id(attr_id)
    if row is None:
        return None

    cached = row.get("description_suggestion")
    if cached:
        return cached

    messages = _PROMPT.format_messages(
        max_chars=_DESCRIPTION_SUGGESTION_MAX_CHARS,
        attribute_name=row.get("name", ""),
        term_name=row.get("term_name", ""),
    )

    llm = get_llm_client(temperature=0.0, max_tokens=400)
    response = invoke_with_structured_output(
        llm, messages, _DescriptionSuggestionResponse
    )
    if response is None:
        return None

    suggestion = _fit_description_suggestion(response.description)
    if not suggestion:
        return None

    set_sql_attribute_description_suggestion(attr_id, suggestion)
    return suggestion
