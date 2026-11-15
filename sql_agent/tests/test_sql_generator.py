# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

import asyncio
from typing import Any

import pytest

from sql_agent.modules.repair.policy import INFO_NOT_FOUND
from sql_agent.modules.sql.rewrite import add_filter_columns
from sql_agent.nodes import semantic_search, sql_generator
from sql_agent.nodes.sql_generator import check_sql_generation
from sql_agent.schemas import SQLGeneratorOutput, State
from sql_agent.services.prompt_service import PROMPTS_FILE, load_chat_prompt_template


class FakeGenerator:
    """Stands in for the LLM: returns one fixed output and keeps the prompts."""

    def __init__(self) -> None:
        self.output: SQLGeneratorOutput | None = None
        self.prompts: list[list[Any]] = []

    async def invoke(self, chain: Any, variables: dict) -> Any:
        # The messages the chain would send: the real prompt with these variables.
        prompt = load_chat_prompt_template(PROMPTS_FILE, "sql_generator")
        self.prompts.append(prompt.format_messages(**variables))
        return self.output


@pytest.fixture
def generator(monkeypatch: pytest.MonkeyPatch) -> FakeGenerator:
    fake = FakeGenerator()
    monkeypatch.setattr(sql_generator, "_chain", lambda: None)
    monkeypatch.setattr(sql_generator, "ainvoke_parsed", fake.invoke)
    return fake


def _generate(state: State) -> dict[str, Any]:
    return asyncio.run(sql_generator.sql_generator(state))


def _search(state: State) -> dict[str, Any]:
    return asyncio.run(semantic_search.semantic_search(state))


def _state(**fields: Any) -> State:
    return State(
        user_query="siapa researcher pariwisata",
        schema_context="TABLE riset",
        knowledge_context="DEFINISI BISNIS Researcher",
        semantic_context="<semantic_matches>x</semantic_matches>",
        retry_feedback="<previous_attempt>y</previous_attempt>",
        **fields,
    )


def test_prompt_carries_schema_knowledge_semantics_and_feedback(
    generator: FakeGenerator,
) -> None:
    generator.output = SQLGeneratorOutput(sql_query="SELECT 1")
    _generate(_state())
    system, human = (m.content for m in generator.prompts[0])
    # The system prompt holds only the fixed rules; everything per question,
    # user-editable glossary included, rides in the user turn, question last.
    assert "TABLE riset" not in system and "DEFINISI BISNIS" not in system
    assert "TABLE riset" in human and "DEFINISI BISNIS Researcher" in human
    assert human.rstrip().endswith("</tasks>")
    assert "siapa researcher pariwisata" in human
    assert (
        "<semantic_context>\n<semantic_matches>x</semantic_matches>\n</semantic_context>"
        in human
    )
    assert "<previous_attempt>y</previous_attempt>" in human


def test_placeholders_are_filled_and_raw_sql_kept(generator: FakeGenerator) -> None:
    sql = 'SELECT "a" FROM "t" WHERE "t"."id" IN (__SEMANTIC_1__)'
    generator.output = SQLGeneratorOutput(sql_query=f"```sql\n{sql}\n```")
    update = _generate(_state(semantic_ids={"__SEMANTIC_1__": "1, 2"}))
    assert update["raw_sql_query"] == sql
    assert "IN (1, 2)" in update["sql_query"]
    assert update["error"] is None


def test_cannot_answer_is_information_not_found(generator: FakeGenerator) -> None:
    generator.output = SQLGeneratorOutput(cannot_answer=True, reason="no budget column")
    update = _generate(_state())
    assert update["error_code"] == INFO_NOT_FOUND
    assert "no budget column" in update["error"]


def test_unparsed_output_is_an_error_without_a_code(generator: FakeGenerator) -> None:
    update = _generate(_state())
    assert update["sql_query"] == "" and update["error_code"] is None


def test_routing_after_generation() -> None:
    assert (
        check_sql_generation(State(user_query="q", sql_query="SELECT 1")) == "success"
    )
    missing = State(user_query="q", error_code=INFO_NOT_FOUND)
    assert check_sql_generation(missing) == "renavigate"
    missing.renavigation_count = 1
    assert check_sql_generation(missing) == "fail"


def test_ilike_filter_columns_are_shown() -> None:
    sql = 'SELECT "nama" FROM "t" WHERE "kota" ILIKE \'%bali%\''
    assert add_filter_columns(sql).startswith('SELECT LEFT("kota", 200) AS "kota"')


@pytest.mark.parametrize(
    "sql",
    [
        'SELECT COUNT(*) FROM "t" WHERE "kota" ILIKE \'%bali%\'',
        'SELECT DISTINCT "nama" FROM "t" WHERE "kota" ILIKE \'%bali%\'',
        'SELECT "kota" FROM "t" WHERE "kota" ILIKE \'%bali%\'',
    ],
)
def test_filter_columns_are_left_alone_when_not_needed(sql: str) -> None:
    assert add_filter_columns(sql) == sql


def test_semantic_matches_and_fallback_are_tagged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def rows(ids: dict[str, str], instructions: str) -> Any:
        async def search(state: dict[str, Any]) -> dict[str, Any]:
            return {
                "path_state": {"semantic_ids": ids},
                "semantic_instructions": instructions,
            }

        return search

    monkeypatch.setattr(
        semantic_search, "_search_rows", rows({"__SEMANTIC_1__": "1"}, "m")
    )
    update = _search(State(user_query="q"))
    assert update["semantic_context"] == "<semantic_matches>\nm\n</semantic_matches>"

    monkeypatch.setattr(semantic_search, "_search_rows", rows({}, "use ILIKE"))
    update = _search(State(user_query="q"))
    assert update["semantic_context"].startswith("<semantic_unavailable>")

    monkeypatch.setattr(semantic_search, "_search_rows", rows({}, ""))
    assert _search(State(user_query="q"))["semantic_context"] == ""
