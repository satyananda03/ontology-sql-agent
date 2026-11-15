# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""HTTP entry point for the ``search_database_knowledge`` tool."""

import asyncio
from dataclasses import asdict

from fastapi import APIRouter

from sql_agent.core.config import settings
from sql_agent.schemas import QueryResult, SqlAgentQuery, SqlAgentResult
from sql_agent.services.query_service import answer, render_error

router = APIRouter()

# Questions answered at once; the rest wait their turn inside the timeout below.
_slots = asyncio.Semaphore(settings.sql_agent_max_concurrent)


async def _answer_in_turn(question: str) -> QueryResult:
    async with _slots:
        return await answer(question)


@router.post("/sql-agent/query", response_model=SqlAgentResult)
async def query(body: SqlAgentQuery) -> dict[str, object]:
    """Answer one standalone question from the database.

    The caller rewrites follow-ups into a standalone question first. ``text`` is
    meant to be handed to the calling agent as it is; a failure inside the agent
    comes back as ``status: error`` rather than an HTTP error.
    """
    timeout = settings.sql_agent_timeout_s
    try:
        return asdict(await asyncio.wait_for(_answer_in_turn(body.question), timeout))
    except asyncio.TimeoutError:
        # ponytail: the timeout cancels pending LLM calls, but a step already
        # running in a thread (SQL, retrieval) finishes on its own; a subprocess
        # that can be killed is the upgrade if those pile up.
        return asdict(render_error(f"The query took longer than {timeout:.0f}s."))
