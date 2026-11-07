# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Shared prompt formatters for text-to-SQL agents."""

from __future__ import annotations

from typing import Any

from auto_ontology.utils.sample_values import stringify_sample_values


def _format_sample_values(raw: Any) -> str:
    """Render sample values as ``a, b, c``, or empty when there are none.

    Matches how every other model-facing renderer spells them out (see
    ``auto_ontology.semantic.embed``); interpolating the list itself would leak Python
    repr punctuation into the prompt.
    """
    values = stringify_sample_values(raw)
    if not values:
        return ""
    return ", ".join(values)


def _plain_cell(value: Any) -> str:
    """One pipe-table cell: no newlines, and no ``|`` that would add a column."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        parts = [_plain_cell(item) for item in value]
        return ", ".join(part for part in parts if part)
    return " ".join(str(value).replace("|", "/").split())


def _pipe_table(headers: list[str], rows: list[dict[str, str]]) -> str:
    """Render ``header 1 | header 2`` then one ``|``-separated row per record.

    A header is omitted when every cell under it is empty, so a table with no
    descriptions does not pay for a description column.
    """
    active = [
        header for header in headers if any(row.get(header, "").strip() for row in rows)
    ]
    if not active:
        return ""
    lines = [" | ".join(active)]
    for row in rows:
        lines.append(" | ".join(row.get(header, "") for header in active))
    return "\n".join(lines)


# Dialects whose connection does *not* bind the catalog, so a name has to carry
# it explicitly. These are exactly the connectors that override
# ``SQLDatabase.qualify`` to prepend it (``auto_ontology.connectors.kyuubi``,
# ``auto_ontology.connectors.trino``); everywhere else the session is already scoped to
# the database and a two-part name resolves.
_CATALOG_QUALIFIED_DIALECTS = frozenset({"spark", "trino"})


def qualify_table(
    database_name: str,
    schema_name: str,
    table_name: str,
    dialect: str | None = None,
) -> str:
    """Build the qualified identifier the model is expected to copy verbatim.

    Two-level dialects (MySQL/MariaDB) have no schema namespace: the catalog
    reports ``TABLE_SCHEMA`` as the database itself, so naively joining all
    three parts yields ``db.db.table``, which is a syntax error. The duplicate
    is collapsed for those, and for engines whose connection binds the database
    so that ``schema.table`` still resolves.

    It must *not* be collapsed on a dialect in
    :data:`_CATALOG_QUALIFIED_DIALECTS`. There the catalog and the schema are
    separate namespaces that may legitimately share a name — a Kyuubi catalog
    ``lakehouse`` holding a schema ``lakehouse`` — and the session is left on
    the engine's own default catalog (``spark_catalog``), not the bound one.
    So collapsing emits ``lakehouse.events``, which Spark reads as schema
    ``lakehouse`` under ``spark_catalog`` and rejects with
    TABLE_OR_VIEW_NOT_FOUND. Scoping the session instead is not an option:
    Spark rejects ``USE CATALOG``, and ``SET CATALOG`` leaves
    ``current_schema()`` empty so the two-part name still does not resolve.
    """
    parts = [database_name, schema_name, table_name]
    collapsible = (dialect or "").lower() not in _CATALOG_QUALIFIED_DIALECTS
    if (
        collapsible
        and database_name
        and schema_name
        and database_name.lower() == schema_name.lower()
    ):
        parts = [schema_name, table_name]
    return ".".join(part for part in parts if part)


def _hop_column(
    hop: dict,
    side: str,
    target_db: str | None = None,
    dialect: str | None = None,
) -> str:
    """Format a join-path endpoint, qualified as :func:`qualify_table` would.

    The hop's own database wins over *target_db*, so a path that crosses
    databases names each side correctly; only the bridge-table builder in
    ``auto_ontology.dal.attributes`` omits it, and there *target_db* is the fallback.
    """
    database = hop.get(f"{side}_database") or target_db or ""
    schema = hop.get(f"{side}_schema", "")
    table = hop.get(f"{side}_table", "")
    column = hop.get(f"{side}_column", "")
    prefix = qualify_table(database, schema, table, dialect)
    return f"{prefix}.{column}"


def format_semantic_context(
    primary_attribute: dict,
    attribute_join_paths: list[dict],
    target_db: str | None = None,
    dialect: str | None = None,
) -> str:
    """Format the semantic anchor and verified optional join paths for a prompt.

    Names are qualified exactly as :func:`format_tables_for_prompt` does. The
    prompt tells the model to copy a selected path's verified join conditions,
    so a name spelled differently here than in the schema context is one the
    model may copy into SQL — on a catalog-qualified engine, dropping the catalog
    makes it unresolvable.
    """
    anchor_schema = primary_attribute.get("schema_name", "")
    anchor_table = primary_attribute.get("table_name", "")
    anchor_col = primary_attribute.get("col_name", "")
    anchor_name = primary_attribute.get("attr_name", "")
    anchor_database = primary_attribute.get("database_name") or target_db or ""
    anchor_full = qualify_table(anchor_database, anchor_schema, anchor_table, dialect)
    # Only present on attrs (re-)ingested since this field was added — older
    # rows just omit the tag.
    anchor_datatype = primary_attribute.get("datatype") or ""
    anchor_datatype_tag = f" [{anchor_datatype}]" if anchor_datatype else ""

    lines: list[str] = [
        "SEMANTIC HINT — likely starting table (use as a strong hint, not a mandate):",
        f"  Table: {anchor_full}",
        f"  Column: {anchor_col}  ({anchor_name}){anchor_datatype_tag}",
    ]

    if attribute_join_paths:
        lines.append("")
        lines.append(
            "JOIN PATHS (VERIFIED OPTIONS — derived from the semantic model). "
            "These paths show how available tables can join; they are not a plan "
            "and most may be irrelevant to this question. Select only paths needed "
            "to reach tables that contribute to the answer. Never add a path merely "
            "because it is listed. When a path is needed, use its exact join "
            "conditions. A selected path is indivisible: keep every intermediate "
            "bridge table and every hop. Never shorten it or join its endpoints "
            "directly:"
        )
        for entry in attribute_join_paths:
            attr_name = entry.get("attr_name", "")
            col_name = entry.get("col_name", "")
            schema = entry.get("schema_name", "")
            table = entry.get("table_name", "")
            datatype = entry.get("datatype") or ""
            datatype_tag = f" [{datatype}]" if datatype else ""
            # Structural entries (hub-sibling / bridge-table reconciliation)
            # carry only "path" — no named attribute they resolve to. Render
            # a generic label instead of a blank "  : ." header line.
            if attr_name or col_name or table:
                database = entry.get("database_name") or target_db or ""
                full_table = qualify_table(database, schema, table, dialect)
                lines.append(f"  {attr_name}: {full_table}.{col_name}{datatype_tag}")
            else:
                lines.append("  (structural bridge — connects tables kept above)")
            path = entry.get("path") or []
            if path:
                lines.append("    Join path:")
                for hop in path:
                    left = _hop_column(hop, "source", target_db, dialect)
                    right = _hop_column(hop, "target", target_db, dialect)
                    lines.append(f"      {left} = {right}")

    return "\n".join(lines)


_TABLE_HEADERS = ["table", "label", "description", "primary key"]
_COLUMN_HEADERS = [
    "column",
    "type",
    "is_nullable",
    "foreign key",
    "description",
    "sample values",
    "format",
]
_JSONB_SAMPLE_NOTE = (
    "JSONB sample values are keys (dot = nesting level, use as "
    "->>'key' or ->'container'->>'leaf')."
)


def _column_row(column: Any) -> dict[str, str]:
    if not isinstance(column, dict):
        return {"column": _plain_cell(column)}
    description = _plain_cell(column.get("description"))
    notation = _plain_cell(column.get("format"))
    if notation and "format:" in description.lower():
        notation = ""
    nullability = column.get("is_nullable")
    if nullability is True:
        nullable = "true"
    elif nullability is False:
        nullable = "false"
    else:
        nullable = "unknown"
    return {
        "column": _plain_cell(column.get("name", "UNKNOWN")),
        "type": _plain_cell(column.get("data_type", "UNKNOWN")),
        "is_nullable": nullable,
        "foreign key": _plain_cell(column.get("semantic_fk")),
        "description": description,
        "sample values": _plain_cell(
            _format_sample_values(column.get("sample_values"))
        ),
        "format": notation,
    }


def format_tables_for_prompt(
    tables: list[dict],
    target_db: str | None = None,
    dialect: str | None = None,
) -> str:
    """Format tables and their columns as schema context for a prompt.

    *dialect* only decides how each table name is qualified; see
    :func:`qualify_table`. Omitting it keeps the two-part form, which is wrong
    for a catalog-qualified engine, so callers that have a connector should
    pass its dialect.

    *target_db* stands in for a table that carries no ``database_name`` of its
    own, which legacy catalog metadata does not (see
    ``connector_routing.resolve_connector_from_tables``). Without it such a
    table renders unqualified here while :func:`format_semantic_context` names
    the same table with its catalog — and on a catalog-qualified engine the
    short one does not resolve.
    """
    if not tables:
        return "No tables available"

    formatted_tables = []
    for table in tables:
        table_name = table.get("name", "UNKNOWN")
        table_label = table.get("label", "")
        database_name = table.get("database_name") or target_db or ""
        schema_name = table.get("schema_name", "")
        full_name = qualify_table(database_name, schema_name, table_name, dialect)
        blocks = [
            _pipe_table(
                _TABLE_HEADERS,
                [
                    {
                        "table": _plain_cell(full_name),
                        "label": _plain_cell(
                            table_label if table_label != table_name else ""
                        ),
                        "description": _plain_cell(table.get("description")),
                        "primary key": _plain_cell(table.get("pk")),
                    }
                ],
            )
        ]

        columns = table.get("columns")
        if not isinstance(columns, list):
            columns = []
        if columns:
            column_rows = [_column_row(column) for column in columns]
            blocks.append(_pipe_table(_COLUMN_HEADERS, column_rows))
            if any("json" in row["type"].lower() for row in column_rows):
                blocks.append(_JSONB_SAMPLE_NOTE)

        formatted_tables.append("\n".join(block for block in blocks if block))

    return "\n\n".join(formatted_tables)
