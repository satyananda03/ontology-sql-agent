# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Retrieval results per question, so a repeated question skips the retrieval agents.

The same idea as ``classic_sql_agent``'s schema navigator cache. Keys are the exact
question after case and whitespace are normalized, not a similarity match: two
close questions can need different tables (per region vs per year), and a wrong
hit costs more than a miss.

Only ``path_state`` is per question and later steps write into it (semantic ids,
thoughts), so it is copied on the way in and out. The rest of the agent state is
shared clients (LLM, connectors, retrievers) and is reused as is.
"""

import copy
import time
from collections import OrderedDict
from typing import Any

from sql_agent.core.logging import get_logger

logger = get_logger(__name__)

MAX_ENTRIES = 256
# ponytail: TTL only; invalidate on catalog or glossary edits if stale tables become a problem.
TTL_S = 600.0

_entries: "OrderedDict[str, tuple[float, dict[str, Any]]]" = OrderedDict()


def _key(question: str) -> str:
    return " ".join(question.lower().split())


def _copy(ontology: dict[str, Any]) -> dict[str, Any]:
    return {**ontology, "path_state": copy.deepcopy(ontology.get("path_state", {}))}


def get(question: str) -> dict[str, Any] | None:
    """The cached retrieval result for *question*, or None."""
    key = _key(question)
    entry = _entries.get(key)
    if entry is None or time.monotonic() - entry[0] > TTL_S:
        _entries.pop(key, None)
        logger.info("[CACHE] retrieval miss")
        return None
    _entries.move_to_end(key)
    logger.info("[CACHE] retrieval hit")
    return _copy(entry[1])


def put(question: str, ontology: dict[str, Any]) -> None:
    """Remember *ontology* as the retrieval result for *question*."""
    key = _key(question)
    _entries[key] = (time.monotonic(), _copy(ontology))
    _entries.move_to_end(key)
    while len(_entries) > MAX_ENTRIES:
        _entries.popitem(last=False)


def clear() -> None:
    _entries.clear()
