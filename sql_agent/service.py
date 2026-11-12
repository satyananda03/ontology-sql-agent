# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Run the graph and render its result for a calling agent."""

import logging
import time
from dataclasses import dataclass
from typing import Any, Literal

from sql_agent.nodes.repair import INFO_NOT_FOUND, MISSING_OBJECT_CODES
from sql_agent.semantic_rows import SEMANTIC_TRUNCATED_NOTE
from sql_agent.state import State
from sql_agent.utils import max_rows
from sql_agent.workflow import get_workflow

logger = logging.getLogger(__name__)

Status = Literal["ok", "empty", "unanswerable", "error"]

RECURSION_LIMIT = 50
_SEMANTIC_CUT_NOTE = (
    "CATATAN : pencarian topik mencapai batasnya, jadi daftar ini mungkin belum "
    "lengkap.\n"
)


@dataclass(frozen=True)
class QueryResult:
    """One answered question. ``text`` is what the calling agent reads."""

    status: Status
    text: str
    sql: str = ""
    row_count: int = 0
    truncated: bool = False


def render_error(message: str) -> QueryResult:
    """Tell the calling agent that the failure was not caused by its wording."""
    return QueryResult(
        status="error",
        text=f"STATUS: error\nERROR: {message}\n"
        "Kegagalan terjadi di server, bukan karena kata-kata pertanyaan. Coba sekali "
        "lagi; kalau tetap gagal, laporkan database sedang tidak tersedia.",
    )


def run(question: str) -> dict[str, Any]:
    """The graph's final state for one standalone question."""
    request = State(user_query=question)
    started = time.perf_counter()
    try:
        return get_workflow().invoke(
            request, config={"recursion_limit": RECURSION_LIMIT}
        )
    finally:
        logger.info(f"[TIMING] sql_agent total {time.perf_counter() - started:.2f}s")


def _semantic_search_was_cut(state: dict[str, Any]) -> bool:
    thoughts = state.get("ontology", {}).get("path_state", {}).get("thoughts_log")
    return SEMANTIC_TRUNCATED_NOTE in str(thoughts or "")


def to_query_result(state: dict[str, Any]) -> QueryResult:
    """Map the graph's final state onto the tool's response."""
    sql = state.get("sql_query") or ""
    answer = state.get("answer")
    if answer is None:
        # Safety stopped a statement that was not a read-only query.
        return QueryResult(
            status="error",
            sql=sql,
            text=f"STATUS: error\nERROR: {state.get('error')}\n"
            "Perjelas maksud pertanyaan, lalu panggil tool ini lagi.",
        )
    if state.get("sql_execution_status") != "success":
        missing = state.get("error_code") in (INFO_NOT_FOUND, *MISSING_OBJECT_CODES)
        return QueryResult(
            status="unanswerable" if missing else "error", sql=sql, text=answer
        )

    rows = (state.get("sql_execution_result") or {}).get("data") or []
    if not rows:
        return QueryResult(status="empty", sql=sql, text=answer)
    semantic_cut = _semantic_search_was_cut(state)
    return QueryResult(
        status="ok",
        sql=sql,
        row_count=len(rows),
        truncated=len(rows) > max_rows() or semantic_cut,
        text=(_SEMANTIC_CUT_NOTE if semantic_cut else "") + answer,
    )


def warm_up() -> None:
    """Pay the first query's setup cost up front: graph, LLM clients, DB/VDB pools."""
    from sql_agent import retrieval
    from sql_agent.nodes import sql_generator

    started = time.perf_counter()
    try:
        get_workflow()
        sql_generator._llm()
        retrieval.warm_up()
    except Exception:  # noqa: BLE001 — warm-up is best effort; queries still work
        logger.warning("SQL agent warm-up failed", exc_info=True)
        return
    logger.info(f"[TIMING] sql_agent warm-up {time.perf_counter() - started:.2f}s")


def answer(question: str) -> QueryResult:
    """Answer one standalone question from the database."""
    try:
        state = run(question)
    except Exception as error:  # noqa: BLE001 — the tool reports, it does not crash
        logger.exception("SQL agent failed")
        return render_error(str(error))
    return to_query_result(state)
