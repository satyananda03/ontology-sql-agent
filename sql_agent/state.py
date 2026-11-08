# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class State(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # ─── Request ───
    user_query: str
    evidence: str = ""
    # ─── Ontology context (nodes/ontology_context.py) ───
    # auto_ontology's agent state. Its retrieval agents read and write it, and
    # semantic search reuses the tables they found.
    ontology: dict[str, Any] = Field(default_factory=dict)
    connector: Any = None
    selected_table: list[str] = Field(default_factory=list)
    schema_context: str = ""
    knowledge_context: str = ""
    # ─── Semantic search (nodes/semantic_search.py) ───
    semantic_context: str = ""
    # placeholder -> daftar ID literal; diganti kode setelah SQL ditulis,
    # supaya ID (bisa puluhan UUID) tidak pernah disalin ulang oleh LLM.
    semantic_ids: dict[str, str] = Field(default_factory=dict)
    # ─── SQL pipeline ───
    sql_query: str | None = None
    raw_sql_query: str | None = None
    sql_safety_status: Literal["safe", "unsafe"] | None = None
    sql_syntax_status: Literal["valid", "invalid"] | None = None
    sql_execution_status: Literal["success", "failure"] | None = None
    sql_execution_result: dict[str, Any] | None = None
    # ─── Loop perbaikan (error & hasil kosong), lihat nodes/repair.py ───
    retry_count: int = 0
    retry_feedback: str | None = None
    error_code: str | None = None  # SQLSTATE Postgres
    last_error: str | None = None
    value_probed: bool = False
    renavigation_count: int = 0
    # ─── Final output ───
    answer: str | None = None
    error: str | None = None
