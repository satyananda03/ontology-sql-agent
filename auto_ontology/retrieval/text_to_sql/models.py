# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, ConfigDict, Field


# ==================== TYPE ALIASES ====================


# ==================== SCORE MODELS ====================


class TableRemovalModel(BaseModel):
    """One table the relevance filter proposes to remove, with its checks.

    A table earns removal only by failing *both* tests, so both are answered
    per table rather than summarised once for the batch. An audit of 47
    harmful drops found 33 of them (70%) were tables the gold query used only
    to restrict rows, never to supply a projected column: asked for a single
    free-form justification the model reliably reasons about column
    provenance alone and stops there, which is exactly the blind spot.
    ``candidates_preparation`` enforces the two flags rather than trusting
    the prose, so a removal the model cannot justify is not applied.
    """

    model_config = ConfigDict(extra="forbid")

    table: str = Field(..., description="Name of the table to remove.")
    supplies_no_needed_column: bool = Field(
        ...,
        description=(
            "True only if this table supplies no column the answer needs — "
            "neither in the output, nor in a filter, nor in a grouping or sort."
        ),
    )
    cannot_change_qualifying_rows: bool = Field(
        ...,
        description=(
            "True only if removing this table cannot change WHICH rows qualify. "
            "Joining a table also restricts the result to rows that have a "
            "match in it, so this is False whenever the question limits results "
            "to rows having a related record there (only schools that appear in "
            "frpm; only patients who have an examination record) — even though "
            "none of that table's columns are returned."
        ),
    )
    justification: str = Field(
        ...,
        description=(
            "One sentence stating how you verified the two flags above, "
            "naming the row-scoping check explicitly."
        ),
    )


class TableRelevanceModel(BaseModel):
    """LLM output for table relevance filtering."""

    model_config = ConfigDict(extra="forbid")

    reasoning: str = Field(
        ...,
        description="Brief reasoning (1-2 sentences max) on which tables are relevant.",
    )
    tables_to_remove: list[TableRemovalModel] = Field(
        default_factory=list,
        description=(
            "Tables that can be safely removed, each with its removal checks. "
            "Leave EMPTY [] if unsure or none should be removed."
        ),
    )


class CustomAnalysisRelevanceModel(BaseModel):
    """LLM output for custom analysis relevance filtering."""

    model_config = ConfigDict(extra="forbid")

    reasoning: str = Field(
        ...,
        description="Brief reasoning (1-2 sentences max) on which custom analyses are relevant.",
    )
    analyses_to_remove: list[str] = Field(
        ...,
        description="Names of custom analyses that can be safely removed. Leave empty if unsure.",
    )


class ColumnAttributeSpec(BaseModel):
    """Typed result for a ColumnAttribute hit from the semantic VDB."""

    source_column: str
    name: str
    display_name: str = ""
    datatype: str = ""
    description: str | None = None


class CustomAnalysisFilterModel(BaseModel):
    """LLM structured output for filtering custom analysis candidates by relevance."""

    model_config = ConfigDict(extra="forbid")

    kept_ids: list[str] = Field(
        ...,
        description="IDs of custom analyses that are relevant to the user's question. Empty list if none are relevant.",
    )


class CombinedCandidateFilterModel(BaseModel):
    """LLM structured output for filtering both custom analyses and SQL attributes in one call."""

    model_config = ConfigDict(extra="forbid")

    custom_analysis_ids: list[str] = Field(
        ...,
        description="IDs of custom analyses to KEEP. Empty list if none are relevant.",
    )
    sql_attribute_ids: list[str] = Field(
        ...,
        description="IDs of SQL attributes to KEEP. Empty list if none are relevant.",
    )


class AnchorColumnModel(BaseModel):
    """LLM output for identifying the primary ColumnAttribute for the question."""

    model_config = ConfigDict(extra="forbid")

    reasoning: str = Field(..., description="Brief reasoning (1-2 sentences max).")
    anchor_id: str | None = Field(
        ...,
        description="The id of the ColumnAttribute that is the primary focus of the question.",
    )
