# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from typing import Any

import pytest

from auto_ontology.utils import llm_invoke
from sql_agent.knowledge.generate_synonyms import (
    SynonymProposal,
    clean_synonyms,
    propose,
)


def test_clean_drops_own_name_blanks_and_duplicates() -> None:
    proposed = ["  Peneliti ", "peneliti", "researcher", "RESEARCH  program", " "]
    assert clean_synonyms("Researcher", proposed) == ["Peneliti", "RESEARCH program"]


def test_a_failed_llm_call_proposes_nothing_for_that_term(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results = iter([SynonymProposal(synonyms=["peneliti"]), None])

    def invoke(llm: Any, messages: list, schema: type) -> Any:
        return next(results)

    monkeypatch.setattr(llm_invoke, "invoke_with_structured_output", invoke)
    terms = [
        {"name": "Researcher", "table_name": "riset"},
        {"name": "Event", "table_name": "event", "columns": ["nama"]},
    ]
    assert propose(terms, llm=None) == {"Researcher": ["peneliti"], "Event": []}
