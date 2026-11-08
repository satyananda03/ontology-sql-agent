# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sql_agent.server.connection import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


def test_connection_is_shown_without_its_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CONNECTION_STRINGS", "postgresql://reader:s3cret@db.local:6543/sales"
    )

    response = _client().get("/api/connection")

    assert response.json() == {
        "database": "sales",
        "host": "db.local",
        "port": 6543,
        "user": "reader",
    }
    assert "s3cret" not in response.text


def test_no_connection_is_a_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONNECTION_STRINGS", raising=False)

    assert _client().get("/api/connection").status_code == 404
