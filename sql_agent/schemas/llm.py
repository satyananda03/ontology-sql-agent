# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Keluaran terstruktur yang diminta dari LLM, satu kelas per prompt di ``prompts.yaml``."""

from pydantic import BaseModel, Field


# ─── sql_generator ───
class SQLGeneratorOutput(BaseModel):
    cannot_answer: bool = Field(
        default=False,
        description=(
            "true if the tables/columns in the schema context do not contain the "
            "information asked. Then leave sql_query empty — never write a "
            "placeholder query such as SELECT 0 or SELECT NULL."
        ),
    )
    reason: str = Field(
        default="",
        description="When cannot_answer is true: which information is missing from the schema.",
    )
    sql_query: str = Field(
        default="",
        description=(
            "The complete PostgreSQL query string (empty when cannot_answer is true). "
            "Use double quotes for schema, table, and column names, example : "
            '{"sql_query": "SELECT \\"id\\" FROM \\"data_iccn_user\\".\\"profiles\\";"}'
            "Always prefix tables with the exact schema name from the provided context"
        ),
    )


# ─── semantic_planner ───
class SemanticFilter(BaseModel):
    table: str = Field(description="Table that owns the searchable column.")
    column: str = Field(description="Searchable column name, exactly as listed.")
    query: str = Field(description="Core phrase plus close synonyms or subtopics.")


class SemanticPlan(BaseModel):
    filters: list[SemanticFilter] = Field(default_factory=list)


# ─── semantic_verifier ───
class RelevantCandidates(BaseModel):
    reasoning: str = Field(
        description="One short line per matching candidate: '<number>: <why>'."
    )
    numbers: list[int] = Field(
        description="Numbers of the candidates that genuinely match. Empty if none."
    )
