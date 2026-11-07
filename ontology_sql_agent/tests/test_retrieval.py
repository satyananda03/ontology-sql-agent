# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any

import pytest

from ontology_sql_agent import retrieval


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

    state = retrieval.retrieve("q", target_db="db", evidence="rule")

    assert requests == [{"question": "q", "target_db": "db", "evidence": "rule"}]
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
    import auto_ontology.server.settings_dal as settings_dal
    import auto_ontology.utils as utils

    glossary = [{"acronym": "PR", "definition": "pelaku kreatif"}]
    monkeypatch.setattr(connectors_module, "get_connectors", lambda: connectors)
    monkeypatch.setattr(settings_dal, "fetch_acronyms", lambda: glossary)
    monkeypatch.setattr(utils, "get_data_objects_retriever", lambda: "data")
    monkeypatch.setattr(utils, "get_semantic_objects_retriever", lambda: "semantic")
    monkeypatch.setattr(retrieval, "_llm", lambda: "llm")
    return retrieval.build_state("berapa peserta?", **request)


def test_state_carries_what_the_retrieval_agents_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _build_state(monkeypatch, [_Connector("iccn")], evidence="rule")

    assert state["initial_question"] == "berapa peserta?"
    assert state["evidence"] == "rule"
    assert state["path_state"] == {
        "processing_question": "berapa peserta?",
        "target_db": "iccn",
    }
    assert state["glossary"] == state["domain_rules"]
    assert state["glossary"] is not state["domain_rules"]


def test_target_db_is_matched_against_the_configured_databases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connectors = [_Connector("iccn"), _Connector("other")]

    state = _build_state(monkeypatch, connectors, target_db="ICCN")

    assert state["path_state"]["target_db"] == "iccn"


def test_no_connection_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="No database connection"):
        _build_state(monkeypatch, [])
