# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import threading
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ontology_sql_agent.service import QueryResult
from ontology_sql_agent.server import router as module

URL = "/api/sql-agent/query"
KEY = {"x-api-key": "secret"}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SQL_AGENT_API_KEY", "secret")
    monkeypatch.setattr(
        module,
        "answer",
        lambda question, **_: QueryResult(status="ok", text=f"asked {question}"),
    )
    app = FastAPI()
    app.include_router(module.router, prefix="/api")
    return TestClient(app)


def test_answers_with_the_right_key(client: TestClient) -> None:
    response = client.post(URL, json={"question": "q"}, headers=KEY)
    assert response.status_code == 200
    assert response.json()["text"] == "asked q"


@pytest.mark.parametrize("headers", [{}, {"x-api-key": "wrong"}])
def test_rejects_a_missing_or_wrong_key(client: TestClient, headers: dict) -> None:
    assert client.post(URL, json={"question": "q"}, headers=headers).status_code == 401


def test_fails_closed_without_a_configured_key(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SQL_AGENT_API_KEY")
    assert client.post(URL, json={"question": "q"}, headers=KEY).status_code == 503


@pytest.mark.parametrize("question", ["", "x" * 4001])
def test_rejects_an_out_of_bounds_question(client: TestClient, question: str) -> None:
    response = client.post(URL, json={"question": question}, headers=KEY)
    assert response.status_code == 422


@pytest.fixture
def stalled(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    release = threading.Event()

    def wait(question: str, **_: object) -> QueryResult:
        release.wait(5)
        return QueryResult(status="ok", text="late")

    monkeypatch.setattr(module, "answer", wait)
    monkeypatch.setenv("SQL_AGENT_TIMEOUT_S", "0.01")
    yield
    release.set()


def test_timeout_is_reported_as_a_tool_error(client: TestClient, stalled: None) -> None:
    response = client.post(URL, json={"question": "q"}, headers=KEY)
    assert response.status_code == 200
    assert response.json()["status"] == "error"
