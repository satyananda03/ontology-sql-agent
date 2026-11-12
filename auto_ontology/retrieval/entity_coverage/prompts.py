"""Prompts for the entity-coverage question_extraction node."""

import os
from pathlib import Path

from langchain_core.messages import BaseMessage

from auto_ontology.utils.prompt_loader import load_chat_prompt_template, load_prompt

# Maximum number of entity noun phrases to extract per question during clarification.
# Raise via CLARIFICATION_MAX_ENTITIES env var for complex multi-metric queries.
# Falls back to SQL_GEN_MAX_ENTITIES (then 5) when unset.
_MAX_ENTITIES: int = int(
    os.environ.get(
        "CLARIFICATION_MAX_ENTITIES",
        os.environ.get("SQL_GEN_MAX_ENTITIES", "5"),
    )
)


_PROMPTS_FILE = Path(__file__).with_name("prompts.yaml")
_PROMPT = load_chat_prompt_template(_PROMPTS_FILE, "question_extraction")
_SECTIONS = load_prompt("question_extraction", _PROMPTS_FILE)["sections"]


def format_glossary_section(glossary: list[dict[str, str]] | None) -> str:
    """Render the user-curated Glossary, or "" when there is nothing to inject.

    Entries are a flat list rather than ``rules_to_text``'s ``## name`` headings,
    which would collide with surrounding ``##`` prompt sections.
    """
    entries = [
        f"- {name}: {(entry.get('description') or '').strip()}"
        for entry in glossary or []
        if (name := (entry.get("name") or "").strip())
    ]
    if not entries:
        return ""
    return _SECTIONS["glossary"].format(definitions="\n".join(entries))


def create_question_extraction_prompt(
    question: str,
    glossary: list[dict[str, str]] | None = None,
    *,
    include_subject: bool = True,
) -> list[BaseMessage]:
    """Sanitize and extract entity noun phrases; optionally also name subject/acronyms.

    Glossary is always injected so the model can resolve abbreviations.
    """
    return _PROMPT.format_messages(
        intro=_SECTIONS["intro_full" if include_subject else "intro_lite"],
        max_entities=_MAX_ENTITIES,
        subject_rules=_SECTIONS["subject_rules"] if include_subject else "",
        glossary_section=format_glossary_section(glossary),
        question=question,
    )
