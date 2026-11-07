# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Carry the classic agent's hand-written knowledge into the ontology.

Prints what would change unless ``--apply`` is given. Writes go through the same
services the UI uses, so edited text is embedded again. Safe to run repeatedly:
anything already matching, or certified by a person, is left alone.
"""

from __future__ import annotations

import argparse
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

_DEFAULT_KNOWLEDGE = Path(__file__).with_name("iccn.yaml")
_MIN_DESCRIPTION_WORDS = 4


@dataclass
class Plan:
    attributes: list[dict[str, Any]] = field(default_factory=list)
    terms: list[dict[str, Any]] = field(default_factory=list)
    add_relations: list[dict[str, str]] = field(default_factory=list)
    disable_relations: list[dict[str, str]] = field(default_factory=list)
    sql_attributes: list[dict[str, str]] = field(default_factory=list)
    glossary: list[dict[str, str]] = field(default_factory=list)


def _clean(text: Any) -> str:
    return " ".join(str(text or "").split())


def plan_descriptions(
    dictionary: dict[str, Any],
    attributes: list[dict[str, Any]],
    terms: list[dict[str, Any]],
    plan: Plan,
    table_overrides: dict[str, str],
) -> None:
    """Pick the human descriptions worth keeping over the generated ones.

    A label such as "Primary Key" says less than the generated sentence, so very
    short text is skipped. Reviewed definitions are never overwritten, and
    *table_overrides* replaces a table description the dictionary got wrong.
    """
    tables: dict[str, Any] = {}
    for schema in dictionary.get("schemas", {}).values():
        tables.update(schema.get("tables", {}))

    human_columns = {
        (table_name, column["name"]): _clean(column.get("description"))
        for table_name, table in tables.items()
        for column in table.get("columns", [])
        if not column.get("vector_source")
    }
    for attribute in attributes:
        key = (attribute["table_name"], attribute["column_name"])
        text = human_columns.get(key, "")
        if (
            len(text.split()) >= _MIN_DESCRIPTION_WORDS
            and not attribute.get("certified")
            and _clean(attribute.get("description")) != text
        ):
            plan.attributes.append({**attribute, "new_description": text})

    for term in terms:
        table = tables.get(term["table_name"]) or {}
        text = _clean(
            table_overrides.get(term["table_name"]) or table.get("description")
        )
        if (
            text
            and not term.get("description_certified")
            and _clean(term.get("description")) != text
        ):
            plan.terms.append({**term, "new_description": text})


def build_plan(
    dictionary: dict[str, Any],
    knowledge: dict[str, Any],
    attributes: list[dict[str, Any]],
    terms: list[dict[str, Any]],
) -> Plan:
    plan = Plan(
        add_relations=list((knowledge.get("relations") or {}).get("add") or []),
        disable_relations=list((knowledge.get("relations") or {}).get("disable") or []),
        sql_attributes=list(knowledge.get("sql_attributes") or []),
        glossary=list(knowledge.get("glossary") or []),
    )
    plan_descriptions(
        dictionary,
        attributes,
        terms,
        plan,
        knowledge.get("term_description_overrides") or {},
    )
    return plan


def split_column(reference: str) -> tuple[str, str]:
    """Split ``table.column``, refusing anything else."""
    table, separator, column = reference.partition(".")
    if not (table and separator and column) or "." in column:
        raise ValueError(f"Expected table.column, got {reference!r}")
    return table, column


def _read_store(database: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from sqlalchemy import select

    from auto_ontology.dal import schema as s
    from auto_ontology.dal.session import store

    scope = s.catalog_table.join(
        s.catalog_schema, s.catalog_schema.c.id == s.catalog_table.c.schema_id
    ).join(
        s.catalog_database,
        s.catalog_database.c.id == s.catalog_schema.c.database_id,
    )
    attributes = store().query_read(
        select(
            s.column_attribute.c.id,
            s.column_attribute.c.description,
            s.column_attribute.c.certified,
            s.column_attribute__term.c.term_id,
            s.catalog_column.c.name.label("column_name"),
            s.catalog_table.c.name.label("table_name"),
        )
        .select_from(
            scope.join(
                s.catalog_column, s.catalog_column.c.table_id == s.catalog_table.c.id
            )
            .join(
                s.column__has_attribute,
                s.column__has_attribute.c.column_id == s.catalog_column.c.id,
            )
            .join(
                s.column_attribute,
                s.column_attribute.c.id == s.column__has_attribute.c.attribute_id,
            )
            .join(
                s.column_attribute__term,
                s.column_attribute__term.c.attribute_id == s.column_attribute.c.id,
            )
        )
        .where(s.catalog_database.c.name == database)
    )
    terms = store().query_read(
        select(
            s.term.c.id,
            s.term.c.name,
            s.term.c.description,
            s.term.c.description_certified,
            s.catalog_table.c.name.label("table_name"),
        )
        .select_from(
            scope.join(
                s.table__term, s.table__term.c.table_id == s.catalog_table.c.id
            ).join(s.term, s.term.c.id == s.table__term.c.term_id)
        )
        .where(s.catalog_database.c.name == database)
    )
    return [dict(r) for r in attributes], [dict(r) for r in terms]


def _resolve_edge(edge: dict[str, str], database: str) -> tuple[str, str]:
    """Return ``(source column id, target attribute id)`` for one relation."""
    from auto_ontology.dal.attributes import find_column_attribute_by_column_id
    from auto_ontology.dal.datasources import find_column_id_by_table_and_name

    source = find_column_id_by_table_and_name(*split_column(edge["source"]), database)
    target = find_column_id_by_table_and_name(*split_column(edge["target"]), database)
    attribute = find_column_attribute_by_column_id(target) if target else None
    if not source or not attribute:
        raise ValueError(f"Cannot resolve relation {edge}")
    return source, attribute


def _disable_relation(source_id: str, attribute_id: str) -> None:
    from auto_ontology.dal import schema as s
    from auto_ontology.dal.session import store

    store().query_write(
        s.column__semantic_fk.update()
        .where(
            s.column__semantic_fk.c.column_id == source_id,
            s.column__semantic_fk.c.attribute_id == attribute_id,
        )
        .values(use_in_join_paths=False)
    )


def _write_glossary(entries: list[dict[str, str]]) -> None:
    import psycopg

    from auto_ontology.infra.postgres import (
        FRONTEND_SCHEMA,
        get_postgres_connection_string,
    )

    with psycopg.connect(get_postgres_connection_string()) as connection:
        for entry in entries:
            connection.execute(
                f"INSERT INTO {FRONTEND_SCHEMA}.acronyms "
                "(id, name, description, created_at, updated_at) "
                "VALUES (%s, %s, %s, now(), now()) ON CONFLICT (name) DO UPDATE "
                "SET description = EXCLUDED.description, updated_at = now()",
                (
                    str(uuid.uuid4()),
                    entry["name"],
                    _clean(entry["description"]),
                ),
            )


def apply_plan(plan: Plan, database: str, terms: list[dict[str, Any]]) -> None:
    from auto_ontology.dal.attributes import merge_semantic_fk
    from auto_ontology.dal.terms import update_term
    from auto_ontology.server.sql_attributes.service import (
        SqlAttributeExpressionConflict,
        SqlAttributeNameConflict,
        create_sql_attribute,
    )
    from auto_ontology.server.terms.service import (
        refresh_term_embeddings,
        update_column_attribute,
    )

    for term in plan.terms:
        update_term(term["id"], description=term["new_description"])
        refresh_term_embeddings(term["id"], refresh_dependent_attrs=False)
    for attribute in plan.attributes:
        update_column_attribute(
            attribute["term_id"],
            attribute["id"],
            description=attribute["new_description"],
        )
    for edge in plan.add_relations:
        merge_semantic_fk(*_resolve_edge(edge, database))
    for edge in plan.disable_relations:
        _disable_relation(*_resolve_edge(edge, database))

    term_by_table = {term["table_name"]: term["id"] for term in terms}
    for attribute in plan.sql_attributes:
        try:
            create_sql_attribute(
                name=attribute["name"],
                description=_clean(attribute["description"]),
                expression=_clean(attribute["expression"]),
                term_id=term_by_table[attribute["term_table"]],
                connector=database,
            )
        except (SqlAttributeNameConflict, SqlAttributeExpressionConflict):
            print(f"Already exists: {attribute['name']}")
    _write_glossary(plan.glossary)


def print_plan(plan: Plan, *, show_descriptions: bool) -> None:
    print(f"Term descriptions to replace:      {len(plan.terms)}")
    print(f"Attribute descriptions to replace: {len(plan.attributes)}")
    if show_descriptions:
        for term in plan.terms:
            print(f"  TERM {term['table_name']}: {term['new_description'][:120]}")
        for item in plan.attributes:
            print(
                f"  ATTR {item['table_name']}.{item['column_name']}: "
                f"{item['new_description'][:120]}"
            )
    for edge in plan.add_relations:
        print(f"Add relation:     {edge['source']} -> {edge['target']}")
    for edge in plan.disable_relations:
        print(f"Disable relation: {edge['source']} -> {edge['target']}")
    for attribute in plan.sql_attributes:
        print(f"SQL attribute:    {attribute['name']} on {attribute['term_table']}")
    for entry in plan.glossary:
        print(f"Glossary:         {entry['name']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dictionary", type=Path, required=True)
    parser.add_argument("--knowledge", type=Path, default=_DEFAULT_KNOWLEDGE)
    parser.add_argument("--show-descriptions", action="store_true")
    parser.add_argument("--apply", action="store_true", help="Write the changes.")
    args = parser.parse_args()

    load_dotenv(Path.cwd() / ".env")
    knowledge = yaml.safe_load(args.knowledge.read_text())
    dictionary = yaml.safe_load(args.dictionary.read_text())
    database = knowledge["database"]
    attributes, terms = _read_store(database)
    plan = build_plan(dictionary, knowledge, attributes, terms)
    print_plan(plan, show_descriptions=args.show_descriptions)
    if args.apply:
        apply_plan(plan, database, terms)
        print("Applied.")
    else:
        print("Dry run: nothing was written. Add --apply to write these changes.")


if __name__ == "__main__":
    main()
