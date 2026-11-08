# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""HTTP entry point for the ``search_database_knowledge`` tool."""

from __future__ import annotations

import os
import secrets
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import asdict
from typing import Annotated, Literal

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from sql_agent.service import answer, render_error

router = APIRouter()

_DEFAULT_TIMEOUT_S = 120.0
_executor = ThreadPoolExecutor(
    max_workers=int(os.environ.get("SQL_AGENT_MAX_CONCURRENT") or 4),
    thread_name_prefix="sql-agent",
)


class SqlAgentQuery(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    evidence: str = Field(default="", max_length=8000)


class SqlAgentResult(BaseModel):
    status: Literal["ok", "empty", "unanswerable", "error"]
    text: str
    sql: str = ""
    row_count: int = 0
    truncated: bool = False


def _require_api_key(provided: str | None) -> None:
    """Fail closed: this route runs agent-written SQL against the database."""
    expected = os.environ.get("SQL_AGENT_API_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="SQL_AGENT_API_KEY is not set.")
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid API key.")


@router.post("/sql-agent/query", response_model=SqlAgentResult)
def query(
    body: SqlAgentQuery,
    x_api_key: Annotated[str | None, Header()] = None,
) -> dict[str, object]:
    """Answer one standalone question from the database.

    The caller rewrites follow-ups into a standalone question first. ``text`` is
    meant to be handed to the calling agent as it is; a failure inside the agent
    comes back as ``status: error`` rather than an HTTP error.
    """
    _require_api_key(x_api_key)
    future = _executor.submit(answer, body.question, evidence=body.evidence)
    timeout = float(os.environ.get("SQL_AGENT_TIMEOUT_S") or _DEFAULT_TIMEOUT_S)
    try:
        return asdict(future.result(timeout=timeout))
    except FutureTimeout:
        # ponytail: the run keeps its worker until it ends; a subprocess that can
        # be killed, like the chat worker, is the upgrade if this starves the pool.
        return asdict(render_error(f"The query took longer than {timeout:.0f}s."))
