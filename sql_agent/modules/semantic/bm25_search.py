# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""BM25 arm of the row search: keyword match on ``<source>_bm25`` (ParadeDB pg_search).

The column is written by the warehouse pipeline (normalized text of ``<source>``,
bm25-indexed with the primary key as ``key_field``), the same contract as
``classic_sql_agent``. It is excluded from the ontology catalog, so whether a table
has one is asked of the source database itself.

The query text goes in as-is: ``|||`` is an OR match, so stopwords and punctuation
do no harm, and the planner's synonyms widen recall.
"""

from typing import Any

from auto_ontology.utils.sql_identifiers import quoted_identifier
from sql_agent.modules.semantic.vector_search import SEARCH_TIMEOUT_S, SNIPPET_CHARS

BM25_SUFFIX = "_bm25"

# ponytail: cached for the life of the process; a bm25 column added later needs a restart.
_columns: dict[tuple, str | None] = {}


def bm25_column(connector: Any, spec: dict) -> str | None:
    """Name of the BM25 column for ``spec``'s source column, or None if the table has none."""
    table = spec["table"]
    name = spec["source"] + BM25_SUFFIX
    key = (connector.database_name, table.get("schema_name"), table["name"], name)
    if key not in _columns:
        frame = connector.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = %s AND column_name = %s",
            [table.get("schema_name"), table["name"], name],
            timeout_s=SEARCH_TIMEOUT_S,
        )
        _columns[key] = name if len(frame) else None
    return _columns[key]


def keyword_rows(
    connector: Any, spec: dict, column: str, query: str, k: int
) -> list[dict]:
    """``(id, snippet)`` of the *k* rows scoring highest for *query* on *column*."""
    table = spec["table"]
    pk = quoted_identifier(spec["pk"], "postgres")
    source = quoted_identifier(spec["source"], "postgres")
    target = quoted_identifier(column, "postgres")
    relation = connector.qualify(table.get("schema_name"), table["name"])
    frame = connector.execute(
        f"SELECT {pk} AS id, left({source}::text, {SNIPPET_CHARS}) AS snippet "
        f"FROM {relation} WHERE {target} ||| %s::text "
        f"ORDER BY pdb.score({pk}) DESC LIMIT %s",
        [query, k],
        timeout_s=SEARCH_TIMEOUT_S,
    )
    return frame.to_dict("records") if len(frame) else []
