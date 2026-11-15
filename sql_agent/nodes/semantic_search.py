# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Topik yang dicocokkan lewat makna -> ID baris untuk generator.

Pencariannya dikerjakan ``modules/semantic/rows.py``. Tanpa schema navigator tidak
ada lagi yang menulis ``semantic_filters``, jadi pencarian itu sendiri yang memutuskan
perlu tidaknya mencari, dan hanya untuk tabel terpilih yang punya kolom ``*_vector``.
"""

from typing import Any

from sql_agent.modules.semantic.rows import semantic_rows
from sql_agent.schemas import State

_search_rows = semantic_rows


async def semantic_search(state: State) -> dict[str, Any]:
    update = await _search_rows(state.ontology)
    context = update.get("semantic_instructions") or ""
    ids = update.get("path_state", {}).get("semantic_ids") or {}
    if not context:
        return {"semantic_context": "", "semantic_ids": {}}
    tag = "semantic_matches" if ids else "semantic_unavailable"
    return {"semantic_context": f"<{tag}>\n{context}\n</{tag}>", "semantic_ids": ids}
