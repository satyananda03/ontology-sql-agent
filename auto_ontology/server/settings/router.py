# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Glossary acronyms and instance settings, for the review UI.

Upstream these were Next.js routes writing through Prisma; this repository has
no Next.js, so they live here. Storage is ``frontend.acronyms`` and
``frontend.configurations`` via :mod:`auto_ontology.server.settings_dal`.

Settings are read back through the same functions the services use
(``feature_flags`` and the ingestion config), so the values shown are the ones
in effect, defaults included, and the bounds cannot drift from the readers'.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from auto_ontology.infra.feature_flags import (
    DISTINCT_VALUE_PROBING_ENABLED_KEY,
    MAX_SQL_QUERY_TIMEOUT_SECONDS,
    MIN_SQL_QUERY_TIMEOUT_SECONDS,
    PII_DETECTION_ENABLED_KEY,
    SQL_QUERY_TIMEOUT_SECONDS_KEY,
    get_sql_query_timeout_seconds,
    is_distinct_value_probing_enabled,
    is_pii_detection_enabled,
)
from auto_ontology.ingestion_service.config import (
    SEMANTIC_COMPILATION_ENABLED_KEY,
    is_semantic_compilation_enabled,
)
from auto_ontology.server import settings_dal

router = APIRouter()

Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)]
Timeout = Annotated[
    int, Field(ge=MIN_SQL_QUERY_TIMEOUT_SECONDS, le=MAX_SQL_QUERY_TIMEOUT_SECONDS)
]


class Acronym(BaseModel):
    """One glossary entry the SQL agent reads on every question."""

    id: UUID
    name: str
    description: str
    created_at: datetime
    updated_at: datetime


class AcronymCreate(BaseModel):
    name: Name
    description: Description = ""


class AcronymUpdate(BaseModel):
    """Fields to change; an omitted field keeps its value."""

    name: Name | None = None
    description: Description | None = None


class Settings(BaseModel):
    """The settings in effect, defaults included."""

    semantic_compilation_enabled: bool
    distinct_value_probing_enabled: bool
    pii_detection_enabled: bool
    sql_query_timeout_seconds: int


class SettingsUpdate(BaseModel):
    """Settings to change; an omitted one keeps its value."""

    model_config = ConfigDict(extra="forbid")

    semantic_compilation_enabled: bool | None = None
    distinct_value_probing_enabled: bool | None = None
    pii_detection_enabled: bool | None = None
    sql_query_timeout_seconds: Timeout | None = None


# The model's field names are the stored keys; spelled out so a rename on
# either side fails the import instead of writing a key nothing reads.
_KEYS = {
    "semantic_compilation_enabled": SEMANTIC_COMPILATION_ENABLED_KEY,
    "distinct_value_probing_enabled": DISTINCT_VALUE_PROBING_ENABLED_KEY,
    "pii_detection_enabled": PII_DETECTION_ENABLED_KEY,
    "sql_query_timeout_seconds": SQL_QUERY_TIMEOUT_SECONDS_KEY,
}


def _taken(name: str) -> HTTPException:
    return HTTPException(status_code=409, detail=f"Acronym '{name}' already exists.")


@router.get("/acronyms", response_model=list[Acronym])
def list_acronyms() -> list[dict[str, Any]]:
    """Return every glossary acronym, ordered by name."""
    return settings_dal.list_acronyms()


@router.post("/acronyms", response_model=Acronym, status_code=201)
def create_acronym(body: AcronymCreate) -> dict[str, Any]:
    """Add one acronym; 409 when the name is taken."""
    try:
        return settings_dal.create_acronym(body.name, body.description)
    except UniqueViolation:
        raise _taken(body.name) from None


@router.patch("/acronyms/{acronym_id}", response_model=Acronym)
def update_acronym(acronym_id: UUID, body: AcronymUpdate) -> dict[str, Any]:
    """Rename or redescribe one acronym; 404 when absent, 409 on a taken name."""
    try:
        row = settings_dal.update_acronym(
            acronym_id, name=body.name, description=body.description
        )
    except UniqueViolation:
        raise _taken(body.name or "") from None
    if row is None:
        raise HTTPException(status_code=404, detail="Acronym not found.")
    return row


@router.delete("/acronyms/{acronym_id}", status_code=204)
def delete_acronym(acronym_id: UUID) -> Response:
    """Remove one acronym; 404 when absent."""
    if not settings_dal.delete_acronym(acronym_id):
        raise HTTPException(status_code=404, detail="Acronym not found.")
    return Response(status_code=204)


@router.get("/settings", response_model=Settings)
def read_settings() -> Settings:
    """Return the settings in effect, defaults included."""
    return Settings(
        semantic_compilation_enabled=is_semantic_compilation_enabled(),
        distinct_value_probing_enabled=is_distinct_value_probing_enabled(),
        pii_detection_enabled=is_pii_detection_enabled(),
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
