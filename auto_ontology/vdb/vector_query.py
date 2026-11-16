"""Vector k-NN search on a vdb collection, without langchain-postgres.

:meth:`PostgresVDB.retrieval` used to go through
``PGVectorStore.similarity_search_with_score_by_vector``, which costs far more
than the search itself (0.85 ms on the server):

- it always selects the ``embedding`` column, about 166 KB per 10 hits, which
  no retrieval caller reads;
- its sync API runs every call on one process-wide event-loop thread, so
  concurrent searches from every request queue behind each other.

This module runs the same search on a plain psycopg connection and selects only
what a hit needs. A hit has the shape langchain gives it, so callers see no
difference. Filters it cannot translate are left to langchain (see
:func:`metadata_filter`).
"""

from collections.abc import Sequence
from typing import Any

from psycopg import Connection, sql


def metadata_filter(
    where: dict[str, Any] | None, metadata_columns: Sequence[str]
) -> tuple[sql.Composable, list] | None:
    """``WHERE`` clause and parameters for a langchain-style metadata filter.

    Handles what retrieval sends: string equality on *metadata_columns*.
    Returns ``None`` for anything else (another key, a list, an operator dict),
    so the caller keeps langchain's own semantics there.
    """
    if not where:
        return sql.SQL(""), []
    if not set(where) <= set(metadata_columns) or not all(
        isinstance(value, str) for value in where.values()
    ):
        return None
    clauses = [sql.SQL("{} = %s").format(sql.Identifier(column)) for column in where]
    return sql.SQL(" WHERE ") + sql.SQL(" AND ").join(clauses), list(where.values())


def nearest(
    conn: Connection,
    schema: str,
    table: str,
    vector: list[float],
    top_k: int,
    where: tuple[sql.Composable, list],
    metadata_columns: Sequence[str],
) -> list[dict[str, Any]]:
    """The *top_k* rows closest to *vector* by cosine distance, best first.

    The vector goes in as text and Postgres takes its type from the column, as
    langchain sends it, so a ``vector`` and a ``halfvec`` column both work and
    the HNSW index on either serves the ``ORDER BY``.
    """
    where_sql, where_params = where
    statement = sql.SQL(
        "SELECT content, langchain_metadata, {metadata}, embedding <=> %s AS distance "
        "FROM {table}{where} ORDER BY embedding <=> %s LIMIT %s"
    ).format(
        metadata=sql.SQL(", ").join(map(sql.Identifier, metadata_columns)),
        table=sql.Identifier(schema, table),
        where=where_sql,
    )
    literal = str([float(value) for value in vector])
    with conn.cursor() as cur:
        cur.execute(statement, [literal, *where_params, literal, top_k])
        columns = [column.name for column in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    return [_hit(row, metadata_columns) for row in rows]


def _hit(row: dict[str, Any], metadata_columns: Sequence[str]) -> dict[str, Any]:
    """One row as a retrieval hit, metadata built the way langchain builds it:
    the JSON column, then each metadata column on top."""
    metadata = dict(row["langchain_metadata"] or {})
    for column in metadata_columns:
        metadata[column] = row[column]
    return {
        "text": row["content"],
        "metadata": metadata,
        "_distance": float(row["distance"]),
    }
