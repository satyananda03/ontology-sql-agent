# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Susun konteks skema dan pengetahuan untuk generator dari hasil retrieval ontologi.

Kontrak ke node berikutnya: ``selected_table`` berisi tabel terpilih,
``schema_context`` berisi skemanya, ``knowledge_context`` berisi definisi, jalur
join, sinonim, dan glosarium yang sudah direview.
"""

from typing import Any

from auto_ontology.retrieval.entity_coverage.prompts import format_glossary_section
from auto_ontology.retrieval.text_to_sql.connector_routing import (
    resolve_connector_from_tables,
)
from auto_ontology.retrieval.text_to_sql.formatters_util import (
    format_semantic_context,
    format_tables_for_prompt,
)
from sql_agent.modules.repair.policy import INFO_NOT_FOUND

_NOT_FOUND = "Tidak ada tabel yang memuat informasi ini."


def knowledge_context(
    ontology: dict[str, Any], target_db: str | None, dialect: str | None
) -> str:
    """Reviewed knowledge the generator should prefer over guessing."""
    path_state = ontology.get("path_state", {})
    sections: list[str] = []
    primary_attribute = path_state.get("primary_attribute")
    if primary_attribute:
        sections.append(
            format_semantic_context(
                primary_attribute,
                path_state.get("attribute_join_paths") or [],
                target_db,
                dialect,
            )
        )
    # Saved analyses retrieval matched to this question, as auto_ontology's own
    # SQL step sends them: name, description and SQL, as patterns to follow.
    examples = path_state.get("custom_analyses_str") or []
    if examples:
        sections.append(
            "FEW-SHOT EXAMPLES (analisis tersimpan yang relevan; pakai pola SQL-nya "
            "sebagai panduan dan sesuaikan dengan pertanyaan):\n"
            + "\n".join(f"- {example}" for example in examples)
        )
    sql_attributes = path_state.get("sql_attributes_str") or []
    if sql_attributes:
        sections.append(
            "DEFINISI BISNIS (rumus dan filter yang sudah ditetapkan; pakai SQL-nya "
            "bila sesuai pertanyaan):\n" + "\n".join(sql_attributes)
        )
    synonyms = path_state.get("term_synonyms") or {}
    if synonyms:
        sections.append(
            "SINONIM (nama lain yang dipakai pengguna):\n"
            + "\n".join(
                f"  {term}: {', '.join(names)}" for term, names in synonyms.items()
            )
        )
    sections.append(format_glossary_section(ontology.get("glossary") or []))
    return "\n\n".join(section.strip() for section in sections if section.strip())


def context_update(ontology: dict[str, Any]) -> dict[str, Any]:
    """Map auto_ontology's retrieval result onto the classic state."""
    path_state = ontology.get("path_state", {})
    tables = path_state.get("relevant_tables") or []
    if not tables:
        return {
            "ontology": ontology,
            "selected_table": [],
            "error": _NOT_FOUND,
            "error_code": INFO_NOT_FOUND,
        }
    connector = resolve_connector_from_tables(tables, ontology.get("connectors") or [])
    dialect = getattr(connector, "dialect", None)
    target_db = path_state.get("target_db")
    return {
        "ontology": ontology,
        "connector": connector,
        "selected_table": [table.get("name", "") for table in tables],
        "schema_context": format_tables_for_prompt(tables, target_db, dialect),
        "knowledge_context": knowledge_context(ontology, target_db, dialect),
        "error": None,
        "error_code": None,
    }


def renavigation_question(
    question: str, previous_tables: list[str], error: str | None
) -> str:
    """Pertanyaan yang sama, ditambah catatan kenapa pilihan tabel sebelumnya kurang."""
    return (
        f"{question}\n\n"
        f"Catatan: pilihan tabel sebelumnya {previous_tables} tidak cukup untuk menjawab "
        f"pertanyaan ini ({error}). Pilih tabel yang benar-benar memuat "
        "kolom yang dibutuhkan."
    )
