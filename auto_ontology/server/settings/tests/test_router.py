# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Acronym and settings routes against a real ``frontend`` schema.

Validation tests need no database. The round trips skip unless ``POSTGRES_*``
points at a database migrated to head, where ``frontend.acronyms`` and
``frontend.configurations`` exist.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from uuid import uuid4

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from auto_ontology.infra.postgres import get_postgres_connection_string
from auto_ontology.server.settings import router as module


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(module.router, prefix="/api")
    return TestClient(app)


@pytest.fixture
def frontend_tables() -> Iterator[None]:
    """Skip without the tables; restore both tables' rows afterwards."""
    if not os.environ.get("POSTGRES_USER"):
        pytest.skip("POSTGRES_* not set")
    try:
        conn = psycopg.connect(get_postgres_connection_string(), connect_timeout=3)
        rows = {
            table: conn.execute(f"SELECT * FROM frontend.{table}").fetchall()
            for table in ("acronyms", "configurations")
        }
    except psycopg.Error as exc:
        pytest.skip(f"frontend tables unavailable (alembic upgrade head): {exc}")
    yield
    with conn:
        for table, saved in rows.items():
            conn.execute(f"DELETE FROM frontend.{table}")
            for row in saved:
                marks = ", ".join(["%s"] * len(row))
                conn.execute(f"INSERT INTO frontend.{table} VALUES ({marks})", row)
    conn.close()


@pytest.mark.parametrize(
    "body",
    [
        {"sql_query_timeout_seconds": 0},
        {"sql_query_timeout_seconds": 3601},
        {"pii_detection_enabled": "maybe"},
        {"unknown_setting": True},
    ],
)
def test_settings_refuse_values_the_readers_would_ignore(
    client: TestClient, body: dict
) -> None:
    assert client.patch("/api/settings", json=body).status_code == 422


@pytest.mark.parametrize("body", [{"name": ""}, {"name": "   "}])
def test_an_acronym_needs_a_name(client: TestClient, body: dict) -> None:
    assert client.post("/api/acronyms", json=body).status_code == 422


def test_acronym_round_trip(client: TestClient, frontend_tables: None) -> None:
    name = f"T{uuid4().hex[:8]}"
    created = client.post(
        "/api/acronyms", json={"name": f"  {name} ", "description": "x"}
    )
    assert created.status_code == 201
    acronym = created.json()
    assert acronym["name"] == name

    assert client.post("/api/acronyms", json={"name": name}).status_code == 409

    updated = client.patch(f"/api/acronyms/{acronym['id']}", json={"description": "y"})
    assert updated.json()["name"] == name
    assert updated.json()["description"] == "y"
    assert name in [a["name"] for a in client.get("/api/acronyms").json()]

    assert client.delete(f"/api/acronyms/{acronym['id']}").status_code == 204
    assert client.delete(f"/api/acronyms/{acronym['id']}").status_code == 404
    missing = client.patch(f"/api/acronyms/{uuid4()}", json={"description": "z"})
    assert missing.status_code == 404


def test_settings_are_stored_where_the_readers_look(
    client: TestClient, frontend_tables: None
) -> None:
    response = client.patch(
        "/api/settings",
        json={"pii_detection_enabled": True, "sql_query_timeout_seconds": 45},
    )
    assert response.status_code == 200
    settings = response.json()
    assert settings["pii_detection_enabled"] is True
    assert settings["sql_query_timeout_seconds"] == 45

    client.patch("/api/settings", json={"pii_detection_enabled": False})
    assert client.get("/api/settings").json()["pii_detection_enabled"] is False
