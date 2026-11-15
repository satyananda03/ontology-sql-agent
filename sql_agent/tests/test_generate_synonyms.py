# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

import asyncio
from typing import Any

import pytest

from sql_agent.modules.knowledge import synonyms
from sql_agent.modules.knowledge.synonyms import clean_synonyms, propose
from sql_agent.schemas import SynonymProposal


def test_clean_drops_own_name_blanks_and_duplicates() -> None:
    proposed = ["  Peneliti ", "peneliti", "researcher", "RESEARCH  program", " "]
    assert clean_synonyms("Researcher", proposed) == ["Peneliti", "RESEARCH program"]


def test_a_failed_llm_call_proposes_nothing_for_that_term(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results = iter([SynonymProposal(synonyms=["peneliti"]), None])

    async def invoke(chain: Any, variables: dict) -> Any:
        return next(results)

    monkeypatch.setattr(synonyms, "get_llm", lambda *_, **__: None)
    monkeypatch.setattr(synonyms, "structured_chain", lambda *_: None)
    monkeypatch.setattr(synonyms, "ainvoke_parsed", invoke)
    terms = [
        {"name": "Researcher", "table_name": "riset"},
        {"name": "Event", "table_name": "event", "columns": ["nama"]},
    ]
    assert asyncio.run(propose(terms)) == {"Researcher": ["peneliti"], "Event": []}
