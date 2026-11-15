# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Glossary entries and instance settings, for the review UI.

Storage is the ``glossary`` and ``configuration`` tables, through
:mod:`auto_ontology.dal.settings`.

Settings are read back through the same functions the services use
(``feature_flags`` and the ingestion config), so the values shown are the ones
in effect, defaults included, and the bounds cannot drift from the readers'.
"""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from auto_ontology.infra.feature_flags import (
    DISTINCT_VALUE_PROBING_ENABLED_KEY,
    MAX_SQL_QUERY_TIMEOUT_SECONDS,
    MIN_SQL_QUERY_TIMEOUT_SECONDS,
    SQL_QUERY_TIMEOUT_SECONDS_KEY,
    get_sql_query_timeout_seconds,
    is_distinct_value_probing_enabled,
)
from auto_ontology.dal import settings as settings_dal

router = APIRouter()

Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)]
Timeout = Annotated[
    int, Field(ge=MIN_SQL_QUERY_TIMEOUT_SECONDS, le=MAX_SQL_QUERY_TIMEOUT_SECONDS)
]


class GlossaryEntry(BaseModel):
    """One glossary entry the SQL agent reads on every question."""

    id: UUID
    name: str
    description: str
    created_at: datetime
    updated_at: datetime


class GlossaryEntryCreate(BaseModel):
    name: Name
    description: Description = ""


class GlossaryEntryUpdate(BaseModel):
    """Fields to change; an omitted field keeps its value."""

    name: Name | None = None
    description: Description | None = None


class Settings(BaseModel):
    """The settings in effect, defaults included."""

    distinct_value_probing_enabled: bool
    sql_query_timeout_seconds: int


class SettingsUpdate(BaseModel):
    """Settings to change; an omitted one keeps its value."""

    model_config = ConfigDict(extra="forbid")

    distinct_value_probing_enabled: bool | None = None
    sql_query_timeout_seconds: Timeout | None = None


# The model's field names are the stored keys; spelled out so a rename on
# either side fails the import instead of writing a key nothing reads.
_KEYS = {
    "distinct_value_probing_enabled": DISTINCT_VALUE_PROBING_ENABLED_KEY,
    "sql_query_timeout_seconds": SQL_QUERY_TIMEOUT_SECONDS_KEY,
}


@router.get("/glossary", response_model=list[GlossaryEntry])
def list_glossary() -> list[dict[str, Any]]:
    """Return every glossary entry, ordered by name."""
    return settings_dal.list_glossary()


@router.post("/glossary", response_model=GlossaryEntry, status_code=201)
def create_glossary_entry(body: GlossaryEntryCreate) -> dict[str, Any]:
    """Add one glossary entry; 409 when the name is taken."""
    try:
        return settings_dal.create_glossary_entry(body.name, body.description)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/glossary/{entry_id}", response_model=GlossaryEntry)
def update_glossary_entry(entry_id: UUID, body: GlossaryEntryUpdate) -> dict[str, Any]:
    """Rename or redescribe one glossary entry; 404 when absent, 409 on a taken name."""
    try:
        row = settings_dal.update_glossary_entry(
            str(entry_id), name=body.name, description=body.description
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Glossary entry not found.")
    return row


@router.delete("/glossary/{entry_id}", status_code=204)
def delete_glossary_entry(entry_id: UUID) -> Response:
    """Remove one glossary entry; 404 when absent."""
    if not settings_dal.delete_glossary_entry(str(entry_id)):
        raise HTTPException(status_code=404, detail="Glossary entry not found.")
    return Response(status_code=204)


@router.get("/settings", response_model=Settings)
def read_settings() -> Settings:
    """Return the settings in effect, defaults included."""
    return Settings(
        distinct_value_probing_enabled=is_distinct_value_probing_enabled(),
        sql_query_timeout_seconds=get_sql_query_timeout_seconds(),
    )


@router.patch("/settings", response_model=Settings)
def update_settings(body: SettingsUpdate) -> Settings:
    """Store the given settings and return all of them as now in effect.

    Each applies to the next run that reads it, without a restart.
    """
    for field, value in body.model_dump(exclude_none=True).items():
        stored = str(value).lower() if isinstance(value, bool) else str(value)
        settings_dal.write_configuration(_KEYS[field], stored)
    return read_settings()
