# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Vector arm of the row search: the rows nearest a topic by embedding (pgvector)."""

from typing import Any

from auto_ontology.utils.sql_identifiers import quoted_identifier

SNIPPET_CHARS = 200
SEARCH_TIMEOUT_S = 20.0


def nearest_rows(
    connector: Any, spec: dict, column: str, vector: list[float], k: int
) -> list[dict]:
    """``(id, snippet)`` of the *k* rows whose *column* is closest to *vector*."""
    table = spec["table"]
    pk = quoted_identifier(spec["pk"], "postgres")
    source = quoted_identifier(spec["source"], "postgres")
    target = quoted_identifier(column, "postgres")
    relation = connector.qualify(table.get("schema_name"), table["name"])
    frame = connector.execute(
        f"SELECT {pk} AS id, left({source}::text, {SNIPPET_CHARS}) AS snippet "
        f"FROM {relation} WHERE {target} IS NOT NULL "
        f"ORDER BY {target} <=> %s::vector LIMIT %s",
        [str(vector), k],
        timeout_s=SEARCH_TIMEOUT_S,
    )
    return frame.to_dict("records") if len(frame) else []
