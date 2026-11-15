"""BM25 side of a vdb collection, on ParadeDB ``pg_search``.

Follows ``hybrid_rag_pgsearch``: the row's text is preprocessed in Python
(lowercase, punctuation out, Sastrawi stopwords out) into ``content_cleaned``,
and a ``bm25`` index on the same table covers it. The row itself is created by
:mod:`auto_ontology.vdb.vector_index` (``content`` and ``embedding`` are NOT
NULL), so this module only fills ``content_cleaned`` by ``langchain_id``; a
delete of the row removes it from both indexes at once.

Errors are raised, not logged: a collection that is written must be searchable
by both arms.
"""

import logging
import re
from functools import lru_cache

import psycopg
from psycopg import sql

logger = logging.getLogger(__name__)

COLUMN = "content_cleaned"
KEY_FIELD = "langchain_id"
BATCH_SIZE = 500

# Sastrawi stopwords that carry meaning in a question (negation, existence,
# counts), so they stay searchable.
KEEP = frozenset(
    {"tidak", "belum", "ya", "sudah", "ada", "tanpa", "dua", "kecuali", "nggak", "ok"}
)

_PUNCTUATION = re.compile(r"[^\w\s]")


@lru_cache(maxsize=1)
def stopwords() -> frozenset[str]:
    """Sastrawi's Indonesian stopwords minus :data:`KEEP`, loaded once."""
    from Sastrawi.StopWordRemover.StopWordRemoverFactory import (
        StopWordRemoverFactory,
    )

    return frozenset(StopWordRemoverFactory().get_stop_words()) - KEEP


def preprocess(text: str) -> str:
    """*text* as BM25 indexes it: lowercased, no punctuation, no stopwords."""
    cleaned = _PUNCTUATION.sub(" ", (text or "").lower())
    # split() also drops the double spaces the punctuation pass leaves behind.
    words = stopwords()
    return " ".join(word for word in cleaned.split() if word not in words)


def preprocess_many(texts: list[str]) -> list[str]:
    return [preprocess(text) for text in texts]


def ensure_bm25_index(connection_string: str, schema: str, table: str) -> None:
    """Make *table* BM25-searchable: column, index, and every row filled.

    Checks the catalog before each DDL, so a collection that is already set up
    takes no table lock. ``database_name`` and ``label`` are indexed as
    literals (one untokenized term each), so the filters retrieval always
    applies run inside the index; pg_search allows a single bm25 index per
    table, so they go in now rather than as a rebuild later.
    """
    qualified = sql.Identifier(schema, table)
    index_name = f"ix_bm25_{table}"
    with psycopg.connect(connection_string) as conn:
        with conn.cursor() as cur:
            # Two writers setting up the same collection at once wait here.
            cur.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s))",
                (f"{schema}.{table}.bm25",),
            )
            cur.execute("CREATE EXTENSION IF NOT EXISTS pg_search")
            if not _column_exists(cur, schema, table):
                cur.execute(
                    sql.SQL("ALTER TABLE {table} ADD COLUMN {column} TEXT").format(
                        table=qualified, column=sql.Identifier(COLUMN)
                    )
                )
                logger.info("BM25: added %s to %s.%s", COLUMN, schema, table)
            if not _index_exists(cur, schema, index_name):
                cur.execute(
                    sql.SQL(
                        "CREATE INDEX {name} ON {table} USING bm25 ("
                        "{key}, {column}, "
                        "(database_name::pdb.literal), (label::pdb.literal)"
                        ") WITH (key_field={key_literal})"
                    ).format(
                        name=sql.Identifier(index_name),
                        table=qualified,
                        key=sql.Identifier(KEY_FIELD),
                        column=sql.Identifier(COLUMN),
                        key_literal=sql.Literal(KEY_FIELD),
                    )
                )
                logger.info("BM25: created %s on %s.%s", index_name, schema, table)
            filled = _backfill(cur, qualified)
        conn.commit()
    if filled:
        logger.info("BM25: backfilled %d row(s) in %s.%s", filled, schema, table)


def write_bm25(
    connection_string: str,
    schema: str,
    table: str,
    ids: list[str],
    cleaned: list[str],
) -> None:
    """Store the preprocessed text of rows the vector write just created."""
    with psycopg.connect(connection_string) as conn:
        with conn.cursor() as cur:
            _update(cur, sql.Identifier(schema, table), ids, cleaned)
        conn.commit()


def _column_exists(cur: psycopg.Cursor, schema: str, table: str) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s AND column_name = %s",
        (schema, table, COLUMN),
    )
    return cur.fetchone() is not None


def _index_exists(cur: psycopg.Cursor, schema: str, index_name: str) -> bool:
    cur.execute(
        "SELECT 1 FROM pg_indexes WHERE schemaname = %s AND indexname = %s",
        (schema, index_name),
    )
    return cur.fetchone() is not None


def _backfill(cur: psycopg.Cursor, qualified: sql.Identifier) -> int:
    """Fill ``content_cleaned`` on rows written before it existed, or whose
    BM25 write failed after the vector write. Returns the rows filled."""
    cur.execute(
        sql.SQL("SELECT {key}::text, content FROM {table} WHERE {column} IS NULL").format(
            key=sql.Identifier(KEY_FIELD),
            table=qualified,
            column=sql.Identifier(COLUMN),
        )
    )
    rows = cur.fetchall()
    ids = [row[0] for row in rows]
    _update(cur, qualified, ids, preprocess_many([row[1] for row in rows]))
    return len(rows)


def _update(
    cur: psycopg.Cursor,
    qualified: sql.Identifier,
    ids: list[str],
    cleaned: list[str],
) -> None:
    statement = sql.SQL(
        "UPDATE {table} AS t SET {column} = v.cleaned "
        "FROM unnest(%s::uuid[], %s::text[]) AS v(id, cleaned) "
        "WHERE t.{key} = v.id"
    ).format(
        table=qualified,
        column=sql.Identifier(COLUMN),
        key=sql.Identifier(KEY_FIELD),
    )
    for start in range(0, len(ids), BATCH_SIZE):
        end = start + BATCH_SIZE
        cur.execute(statement, (ids[start:end], cleaned[start:end]))
