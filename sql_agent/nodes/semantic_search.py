# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Topik yang dicocokkan lewat makna -> ID baris untuk generator.

Pencariannya dikerjakan ``sql_agent.semantic_rows``, yang di-port dari node
ini tanpa batas 20 ID. Tanpa schema navigator tidak ada lagi yang menulis
``semantic_filters``, jadi node itu sendiri yang memutuskan perlu tidaknya mencari,
dan hanya untuk tabel terpilih yang punya kolom ``*_vector``.
"""

import logging
from typing import Any

from auto_ontology.retrieval.text_to_sql.base import agent_wrapper
from sql_agent.state import State
from sql_agent.semantic_rows import SemanticRowsAgent

logger = logging.getLogger(__name__)

_search_rows = agent_wrapper(SemanticRowsAgent())


def semantic_search(state: State) -> dict[str, Any]:
    update = _search_rows(state.ontology)
    context = update.get("semantic_instructions") or ""
    ids = update.get("path_state", {}).get("semantic_ids") or {}
    if not context:
        return {"semantic_context": "", "semantic_ids": {}}
    tag = "semantic_matches" if ids else "semantic_unavailable"
    return {"semantic_context": f"<{tag}>\n{context}\n</{tag}>", "semantic_ids": ids}


def fill_semantic_ids(sql: str, ids_by_placeholder: dict[str, str]) -> str:
    """Ganti placeholder ``__SEMANTIC_n__`` dengan daftar ID dari semantic_search."""
    for placeholder, ids in ids_by_placeholder.items():
        if placeholder not in sql:
            logger.warning(f"[SEMANTIC] generator tidak memakai {placeholder}")
        sql = sql.replace(placeholder, ids)
    return sql
