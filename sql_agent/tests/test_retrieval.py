# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from typing import Any

import pytest

from sql_agent.core.config import settings
from sql_agent.modules.retrieval import pipeline as retrieval


def test_retrieval_runs_the_steps_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    ran: list[str] = []

    def step(name: str) -> Any:
        def run(state: dict[str, Any]) -> dict[str, Any]:
            ran.append(name)
            return {"path_state": {name: True}, "decision": name}

        return run

    requests: list[dict[str, Any]] = []

    def build_state(question: str, **request: Any) -> dict[str, Any]:
        requests.append({"question": question, **request})
        return {"path_state": {"processing_question": question}}

    monkeypatch.setattr(retrieval, "RETRIEVAL_STEPS", (step("a"), step("b")))
    monkeypatch.setattr(retrieval, "build_state", build_state)

    state = retrieval.retrieve("q")

    assert requests == [{"question": "q"}]
    assert ran == ["a", "b"]
    assert state["path_state"] == {"processing_question": "q", "a": True, "b": True}
    assert state["decision"] == "b"


class _Connector:
    def __init__(self, database_name: str) -> None:
        self.database_name = database_name
        self.dialect = "postgres"


def _build_state(
    monkeypatch: pytest.MonkeyPatch, connectors: list[_Connector], **request: Any
) -> dict[str, Any]:
    import auto_ontology.connectors as connectors_module
    import auto_ontology.dal.settings as settings_dal
    import auto_ontology.utils as utils

    glossary = [{"name": "PR", "description": "pelaku kreatif"}]
    monkeypatch.setattr(connectors_module, "get_connectors", lambda: connectors)
    monkeypatch.setattr(settings_dal, "fetch_acronyms", lambda: glossary)
    monkeypatch.setattr(utils, "get_data_objects_retriever", lambda: "data")
    monkeypatch.setattr(utils, "get_semantic_objects_retriever", lambda: "semantic")
    monkeypatch.setattr(retrieval, "_llm", lambda: "llm")
    return retrieval.build_state("berapa peserta?", **request)


def test_state_carries_what_the_retrieval_agents_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _build_state(monkeypatch, [_Connector("iccn")])

    assert state["initial_question"] == "berapa peserta?"
    assert state["path_state"] == {
        "processing_question": "berapa peserta?",
        "target_db": "iccn",
    }
    assert state["glossary"] == state["domain_rules"]
    assert state["glossary"] is not state["domain_rules"]


def test_no_connection_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="No database connection"):
        _build_state(monkeypatch, [])


@pytest.mark.parametrize(("configured", "pool"), [(10, 10), (25, 25), (0, None)])
def test_rerank_pool_comes_from_the_settings(
    monkeypatch: pytest.MonkeyPatch, configured: int, pool: int | None
) -> None:
    monkeypatch.setattr(settings, "sql_agent_rerank_pool", configured)
    assert retrieval.rerank_pool() == pool


class _Retriever:
    def __init__(self) -> None:
        self.queries: list[tuple[str, int]] = []

    def query(self, text: str, top_k: int) -> list[dict[str, Any]]:
        self.queries.append((text, top_k))
        return []


def test_warm_up_runs_one_search_on_each_vector_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Building a retriever opens nothing; only a query connects its pool.
    semantic, data = _Retriever(), _Retriever()
    monkeypatch.setattr(
        retrieval,
        "build_state",
        lambda _question: {"semantic_retriever": semantic, "data_retriever": data},
    )

    retrieval.warm_up()

    assert semantic.queries == data.queries == [("warm up", 1)]


@pytest.mark.parametrize(
    ("extracted", "expected"),
    [
        ({"glossary": [{"name": "PR", "description": "pelaku kreatif"}]}, True),
        ({}, False),
    ],
)
def test_domain_rules_follow_the_narrowed_glossary(
    monkeypatch: pytest.MonkeyPatch, extracted: dict[str, Any], expected: bool
) -> None:
    """Narrowed together on success; a failed extraction leaves both full."""
    monkeypatch.setattr(
        retrieval.QuestionExtractionAgent,
        "execute",
        lambda self, state: {"path_state": {}, **extracted},
    )
    state = {"initial_question": "berapa pr?", "path_state": {}}

    result = retrieval.CallerQuestionExtractionAgent().execute(state)

    assert ("domain_rules" in result) is expected
    if expected:
        assert result["domain_rules"] == extracted["glossary"]
