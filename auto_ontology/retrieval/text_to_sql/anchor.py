# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Pick the anchor ColumnAttribute: where every join path starts.

The anchor becomes the primary attribute shown to SQL generation, the source of
each ``find_join_path`` and the table whose hub siblings are expanded. It
should be the column for the question's main subject, which an LLM used to
choose. These rules approximate that choice for free, from signals question
extraction and candidate retrieval already produced: the ``subject`` phrase
and the Term that phrase retrieved.
"""

from typing import Any


def select_anchor(
    hits: list[dict[str, Any]],
    contexts: dict[str, dict[str, Any]],
    subject: str = "",
    subject_term_id: str | None = None,
) -> tuple[str | None, str]:
    """Return ``(attribute_id, rule_name)`` for the anchor.

    *hits* are the retrieved ColumnAttributes, best distance first; only those
    with an entry in *contexts* (their catalog context) can be chosen. Without
    *subject* and *subject_term_id* this is the best-scoring hit.
    """
    subject = subject.casefold().strip()

    def retrieved_by_subject(hit: dict, ctx: dict) -> bool:
        entities = {e.casefold().strip() for e in hit.get("query_entities") or []}
        return bool(subject) and subject in entities

    def belongs_to_subject_term(hit: dict, ctx: dict) -> bool:
        return subject_term_id in ctx.get("term_ids", ())

    # Most specific first. Within a rule the best-scoring hit wins, because the
    # hits arrive sorted by distance.
    rules = [
        ("subject_entity", retrieved_by_subject),
        ("subject_term", belongs_to_subject_term),
        ("top_hit", lambda hit, ctx: True),
    ]
    candidates = [
        (attribute_id, hit, contexts[attribute_id])
        for hit in hits
        if (attribute_id := str(hit.get("id") or "")) in contexts
    ]
    for name, matches in rules:
        for attribute_id, hit, ctx in candidates:
            if matches(hit, ctx):
                return attribute_id, name
    if contexts:
        return next(iter(contexts)), "first_context"
    return None, "none"
