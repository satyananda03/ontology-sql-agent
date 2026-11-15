# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Glossary and settings routes.

Validation tests need no database. The round trips skip unless ``POSTGRES_*``
points at a database migrated to head, where ``glossary`` and ``configuration``
exist.
"""

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
def settings_tables() -> Iterator[None]:
    """Skip without the tables; restore both tables' rows afterwards."""
    if not os.environ.get("POSTGRES_USER"):
        pytest.skip("POSTGRES_* not set")
    try:
        conn = psycopg.connect(get_postgres_connection_string(), connect_timeout=3)
        rows = {
            table: conn.execute(f"SELECT * FROM {table}").fetchall()
            for table in ("glossary", "configuration")
        }
    except psycopg.Error as exc:
        pytest.skip(f"settings tables unavailable (alembic upgrade head): {exc}")
    yield
    with conn:
        for table, saved in rows.items():
            conn.execute(f"DELETE FROM {table}")
            for row in saved:
                marks = ", ".join(["%s"] * len(row))
                conn.execute(f"INSERT INTO {table} VALUES ({marks})", row)
    conn.close()


@pytest.mark.parametrize(
    "body",
    [
        {"sql_query_timeout_seconds": 0},
        {"sql_query_timeout_seconds": 3601},
        {"distinct_value_probing_enabled": "maybe"},
        {"unknown_setting": True},
    ],
)
def test_settings_refuse_values_the_readers_would_ignore(
    client: TestClient, body: dict
) -> None:
    assert client.patch("/api/settings", json=body).status_code == 422


@pytest.mark.parametrize("body", [{"name": ""}, {"name": "   "}])
def test_a_glossary_entry_needs_a_name(client: TestClient, body: dict) -> None:
    assert client.post("/api/glossary", json=body).status_code == 422


def test_glossary_round_trip(client: TestClient, settings_tables: None) -> None:
    name = f"T{uuid4().hex[:8]}"
    created = client.post(
        "/api/glossary", json={"name": f"  {name} ", "description": "x"}
    )
    assert created.status_code == 201
    entry = created.json()
    assert entry["name"] == name

    assert client.post("/api/glossary", json={"name": name}).status_code == 409

    updated = client.patch(f"/api/glossary/{entry['id']}", json={"description": "y"})
    assert updated.json()["name"] == name
    assert updated.json()["description"] == "y"
    assert name in [a["name"] for a in client.get("/api/glossary").json()]

    assert client.delete(f"/api/glossary/{entry['id']}").status_code == 204
    assert client.delete(f"/api/glossary/{entry['id']}").status_code == 404
    missing = client.patch(f"/api/glossary/{uuid4()}", json={"description": "z"})
    assert missing.status_code == 404


def test_settings_are_stored_where_the_readers_look(
    client: TestClient, settings_tables: None
) -> None:
    response = client.patch(
        "/api/settings",
        json={"distinct_value_probing_enabled": False, "sql_query_timeout_seconds": 45},
    )
    assert response.status_code == 200
    settings = response.json()
    assert settings["distinct_value_probing_enabled"] is False
    assert settings["sql_query_timeout_seconds"] == 45

    client.patch("/api/settings", json={"distinct_value_probing_enabled": True})
    assert client.get("/api/settings").json()["distinct_value_probing_enabled"] is True
