# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Pilih tabel dan susun konteks skema dari ontologi, menggantikan schema navigator.

Navigator lama mengirim katalog seluruh tabel ke LLM. Di sini agent retrieval
auto_ontology yang memilih: ekstraksi entitas, pencarian vektor atas Term dan
kolom, lalu graph search untuk jalur join. Kontrak ke node berikutnya tetap sama:
``selected_table`` berisi tabel terpilih, ``schema_context`` berisi skemanya.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from auto_ontology.retrieval.entity_coverage.prompts import format_glossary_section
from auto_ontology.retrieval.text_to_sql.connector_routing import (
    resolve_connector_from_tables,
)
from auto_ontology.retrieval.text_to_sql.formatters_util import (
    format_semantic_context,
    format_tables_for_prompt,
)
from sql_agent import retrieval
from sql_agent.nodes.repair import INFO_NOT_FOUND
from sql_agent.state import State

logger = logging.getLogger(__name__)

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
    if ontology.get("evidence"):
        sections.append(f"ATURAN DARI PEMANGGIL:\n{ontology['evidence']}")
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


def _retrieve(question: str, state: State) -> dict[str, Any]:
    return retrieval.retrieve(question, evidence=state.evidence)


def ontology_context(state: State) -> dict[str, Any]:
    logger.info("Ontology Context - retrieving relevant tables")
    update = context_update(_retrieve(state.user_query, state))
    logger.info(f"Selected tables: {update['selected_table']}")
    return update


def check_schema_navigation(state: State) -> Literal["success", "failure"]:
    return "success" if state.selected_table else "failure"


def schema_renavigator(state: State) -> dict[str, Any]:
    previous = state.selected_table
    count = state.renavigation_count + 1
    logger.info(f"Schema Re-navigator ({count}) - tabel sebelumnya: {previous}")
    note = (
        f"{state.user_query}\n\n"
        f"Catatan: pilihan tabel sebelumnya {previous} tidak cukup untuk menjawab "
        f"pertanyaan ini ({state.error}). Pilih tabel yang benar-benar memuat "
        "kolom yang dibutuhkan."
    )
    update = context_update(_retrieve(note, state))
    update["renavigation_count"] = count
    if update["selected_table"]:
        update.update(retry_feedback=None, last_error=None)
    return update


def check_renavigation(state: State) -> Literal["success", "failure"]:
    return "failure" if state.error else "success"
