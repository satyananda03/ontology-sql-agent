# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ontology_sql_agent.knowledge.import_classic_yaml import (
    _DEFAULT_KNOWLEDGE,
    build_plan,
    split_column,
)

LONG = "Bidang keahlian utama dari peneliti"
DICTIONARY = {
    "schemas": {
        "dwh": {
            "tables": {
                "riset": {
                    "description": "Tabel riset.",
                    "columns": [
                        {"name": "keahlian", "description": LONG},
                        {"name": "detail_id", "description": "Primary Key"},
                        {
                            "name": "keahlian_vector",
                            "description": "Pencarian semantik atas kolom keahlian",
                            "vector_source": "keahlian",
                        },
                    ],
                }
            }
        }
    }
}


def _attribute(column: str, **fields: object) -> dict:
    return {
        "id": column,
        "term_id": "t",
        "table_name": "riset",
        "column_name": column,
        "description": "generated",
        "certified": False,
        **fields,
    }


def _plan(attributes: list[dict], terms: list[dict] | None = None):
    return build_plan(DICTIONARY, {}, attributes, terms or [])


def test_a_real_description_replaces_the_generated_one() -> None:
    plan = _plan([_attribute("keahlian")])
    assert [a["new_description"] for a in plan.attributes] == [LONG]


def test_a_bare_label_does_not_replace_a_generated_sentence() -> None:
    assert _plan([_attribute("detail_id")]).attributes == []


def test_vector_columns_are_ignored() -> None:
    assert _plan([_attribute("keahlian_vector")]).attributes == []


def test_certified_definitions_are_never_overwritten() -> None:
    assert _plan([_attribute("keahlian", certified=True)]).attributes == []


def test_rerun_with_the_same_text_changes_nothing() -> None:
    assert _plan([_attribute("keahlian", description=f"  {LONG} ")]).attributes == []


def test_term_description_comes_from_the_table() -> None:
    term = {"id": "t", "table_name": "riset", "description": ""}
    assert _plan([], [term]).terms[0]["new_description"] == "Tabel riset."


def test_an_override_replaces_the_dictionary_description() -> None:
    term = {"id": "t", "table_name": "riset", "description": ""}
    knowledge = {"term_description_overrides": {"riset": "Teks yang benar."}}
    plan = build_plan(DICTIONARY, knowledge, [], [term])
    assert plan.terms[0]["new_description"] == "Teks yang benar."


def test_reviewed_term_description_is_kept() -> None:
    term = {
        "id": "t",
        "table_name": "riset",
        "description": "x",
        "description_certified": True,
    }
    assert _plan([], [term]).terms == []


@pytest.mark.parametrize("reference", ["column", "a.b.c", ".c", "t."])
def test_relation_references_must_be_table_dot_column(reference: str) -> None:
    with pytest.raises(ValueError):
        split_column(reference)


def test_shipped_knowledge_file_is_well_formed(tmp_path: Path) -> None:
    knowledge = yaml.safe_load(_DEFAULT_KNOWLEDGE.read_text())
    plan = build_plan({}, knowledge, [], [])
    assert plan.add_relations and plan.disable_relations
    for edge in plan.add_relations + plan.disable_relations:
        split_column(edge["source"])
        split_column(edge["target"])
    assert {a["name"] for a in plan.sql_attributes} == {"Researcher"}
    assert set(knowledge["term_description_overrides"]) == {
        "dim_wilayah",
        "fact_insight_ikm",
        "fact_insight_umkm",
    }
    for text in knowledge["term_description_overrides"].values():
        assert "dicocokkan dengan dim_wilayah.kabupaten_kota" not in text
    assert all(entry["description"] for entry in plan.glossary)
