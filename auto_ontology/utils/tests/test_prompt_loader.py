# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Every prompt YAML entry builds, and takes exactly the variables its caller passes.

A stray ``{`` in prompt text, or a renamed variable on one side only, fails here
instead of on the first live LLM call.
"""

from pathlib import Path
from string import Formatter

import pytest

from auto_ontology.utils.prompt_loader import load_chat_prompt_template, load_prompt

REPO = Path(__file__).resolve().parents[3]

# file -> entry -> (template variables, {section: str.format fields})
EXPECTED: dict[str, dict[str, tuple[set[str], dict[str, set[str]]]]] = {
    "auto_ontology/semantic/prompts.yaml": {
        "fk_suggester": (
            {
                "table_header",
                "description",
                "pk_block",
                "known_fk_block",
                "known_fk_lines",
                "all_column_lines",
                "candidate_lines",
            },
            {},
        ),
        "term_extractor": (
            {"table_name", "description", "spec_lines", "domain_block"},
            {"domain_block": {"domains", "core_entities"}},
        ),
        "term_synonyms": ({"description"}, {}),
        "semantic_fk_pick": (
            {
                "column_name",
                "table_name",
                "description",
                "sample_values",
                "candidates_block",
            },
            {},
        ),
        "semantic_fk_join_default": (
            {
                "source_table",
                "source_table_description",
                "target_table",
                "target_table_description",
                "target_column",
                "target_column_description",
                "target_attribute",
                "candidates",
            },
            {},
        ),
        "column_descriptions": ({"columns"}, {}),
        "bridge_sql_attribute": (
            {"bridge_table", "related_tables", "fk_block", "join_hint"},
            {"join_hint_self": set(), "join_hint_default": set()},
        ),
        "sql_attribute_judge": ({"term_name", "term_description", "expr_block"}, {}),
    },
    "auto_ontology/pii_detection/prompts.yaml": {
        "pii_classifier": ({"payload"}, {}),
    },
    "auto_ontology/server/sql_attributes/prompts.yaml": {
        "description_suggestion": ({"max_chars", "attribute_name", "term_name"}, {}),
    },
    "auto_ontology/retrieval/text_to_sql/prompts.yaml": {
        "custom_analysis_relevance": ({"question", "analyses_summary"}, {}),
        "table_relevance": (
            {
                "question",
                "tables_summary",
                "domain_rules",
                "custom_analyses",
                "join_paths",
                "enriched_question",
            },
            {
                "domain_rules": {"rules"},
                "custom_analyses": {"analyses"},
                "join_paths": {"chains"},
                "enriched_question": {"question"},
            },
        ),
        "anchor_column": (
            {"question", "evidence_block", "attributes"},
            {"evidence": {"evidence"}},
        ),
        "candidate_filter": ({"candidate_type", "question", "candidates_block"}, {}),
        "combined_filter": ({"question", "custom_block", "sql_attr_block"}, {}),
    },
    "auto_ontology/retrieval/entity_coverage/prompts.yaml": {
        "question_extraction": (
            {
                "intro",
                "max_entities",
                "subject_rules",
                "glossary_section",
                "evidence_section",
                "question",
            },
            {
                "intro_full": set(),
                "intro_lite": set(),
                "subject_rules": set(),
                "glossary": {"definitions"},
                "evidence": {"evidence"},
            },
        ),
    },
    "sql_agent/prompts.yaml": {
        "sql_generator": (
            {
                "user_query",
                "schema_context",
                "knowledge_context",
                "semantic_context",
                "retry_feedback",
            },
            {},
        ),
        "semantic_planner": ({"question", "columns"}, {}),
        "semantic_verifier": ({"topic", "candidates"}, {}),
        "synonym_proposal": ({"name", "description", "table", "columns"}, {}),
    },
}


def test_every_prompt_file_is_covered() -> None:
    found = {
        str(p.relative_to(REPO))
        for root in ("auto_ontology", "sql_agent")
        for p in (REPO / root).rglob("prompts.yaml")
    }
    assert found == set(EXPECTED)


@pytest.mark.parametrize(
    ("file", "entry"),
    [(f, e) for f, entries in EXPECTED.items() for e in entries],
)
def test_entry_variables_match_callers(file: str, entry: str) -> None:
    variables, sections = EXPECTED[file][entry]
    path = REPO / file

    template = load_chat_prompt_template(path, entry)
    assert set(template.input_variables) == variables
    assert [m.__class__.__name__ for m in template.messages] == [
        "SystemMessagePromptTemplate",
        "HumanMessagePromptTemplate",
    ]

    loaded = load_prompt(entry, path)["sections"]
    assert set(loaded) == set(sections)
    for name, fields in sections.items():
        assert {f for _, f, _, _ in Formatter().parse(loaded[name]) if f} == fields


def test_missing_entry_and_file_raise(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="nope"):
        load_prompt("nope", REPO / "sql_agent/prompts.yaml")
    with pytest.raises(FileNotFoundError):
        load_prompt("x", tmp_path / "missing.yaml")
