# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Kontrak tool ``search_database_knowledge``: permintaan, jawaban, dan hasil service."""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["ok", "empty", "unanswerable", "error"]


@dataclass(frozen=True)
class QueryResult:
    """One answered question. ``text`` is what the calling agent reads."""

    status: Status
    text: str
    sql: str = ""
    row_count: int = 0
    truncated: bool = False


class SqlAgentQuery(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class SqlAgentResult(BaseModel):
    status: Status
    text: str
    sql: str = ""
    row_count: int = 0
    truncated: bool = False
