# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sql_agent.api.routes import query as module
from sql_agent.core.config import settings
from sql_agent.schemas import QueryResult

URL = "/api/sql-agent/query"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    async def answer(question: str) -> QueryResult:
        return QueryResult(status="ok", text=f"asked {question}")

    monkeypatch.setattr(module, "answer", answer)
    app = FastAPI()
    app.include_router(module.router, prefix="/api")
    return TestClient(app)


def test_answers_a_question(client: TestClient) -> None:
    response = client.post(URL, json={"question": "q"})
    assert response.status_code == 200
    assert response.json()["text"] == "asked q"


@pytest.mark.parametrize("question", ["", "x" * 4001])
def test_rejects_an_out_of_bounds_question(client: TestClient, question: str) -> None:
    response = client.post(URL, json={"question": question})
    assert response.status_code == 422


@pytest.fixture
def stalled(monkeypatch: pytest.MonkeyPatch) -> None:
    async def wait(question: str) -> QueryResult:
        await asyncio.sleep(5)
        return QueryResult(status="ok", text="late")

    monkeypatch.setattr(module, "answer", wait)
    monkeypatch.setattr(settings, "sql_agent_timeout_s", 0.01)


def test_timeout_is_reported_as_a_tool_error(client: TestClient, stalled: None) -> None:
    response = client.post(URL, json={"question": "q"})
    assert response.status_code == 200
    assert response.json()["status"] == "error"
