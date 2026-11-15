"""Vector side of a vdb collection: the HNSW index and the embedding write.

:class:`~auto_ontology.vdb.postgres.PostgresVDB` runs this alongside
:mod:`auto_ontology.vdb.bm25_index`; the two share a table and a row id.
"""

import logging

import psycopg
from langchain_postgres import PGVectorStore
from psycopg import sql

logger = logging.getLogger(__name__)


def ensure_hnsw_index(
    connection_string: str, schema: str, table: str, vector_size: int
) -> None:
    """Convert the embedding column to ``halfvec`` and index it with HNSW.

    Without an index every similarity search is a sequential scan over the
    whole collection -- measured at 175ms against 0.36ms indexed on 51,200
    rows, and it degrades linearly from there.

    **The column has to become ``halfvec`` for the index to be reachable**,
    which is not obvious and is worth the ALTER. pgvector caps HNSW at 2000
    dimensions for ``vector`` and the embedding model emits 2048, so the
    only index that can be built over a ``vector(2048)`` column is one over
    a cast expression -- and an expression index is matched *syntactically*,
    so it serves ``embedding::halfvec(2048) <=> $1`` and not the plain
    ``embedding <=> $1`` that ``PGVectorStore`` generates. Postgres then
    silently plans a sequential scan and nothing reports it. Typing the
    column ``halfvec`` instead lets a plain index serve the query the store
    actually writes: the *parameter* is cast (``embedding <=> ($1)::halfvec``),
    which costs nothing, rather than the indexed column.

    The tradeoff is that stored vectors are float16 rather than float32.
    Cosine ranking over 2048 dimensions tolerates that -- it is the same
    approximation the index itself would apply -- but it is a real precision
    change, not just an index.

    Best-effort: a failure here costs latency, not correctness, so it is
    logged and the store still works.
    """
    qualified = sql.Identifier(schema, table)
    index_name = sql.Identifier(f"ix_hnsw_{table}_embedding")
    try:
        with psycopg.connect(connection_string) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL(
                        "ALTER TABLE {table} "
                        "ALTER COLUMN embedding TYPE halfvec({dim})"
                    ).format(table=qualified, dim=sql.Literal(vector_size))
                )
                cur.execute(
                    sql.SQL(
                        "CREATE INDEX IF NOT EXISTS {name} ON {table} "
                        "USING hnsw (embedding halfvec_cosine_ops)"
                    ).format(name=index_name, table=qualified)
                )
            conn.commit()
    except Exception:
        logger.warning(
            "PostgresVDB: could not build the HNSW index on %s.%s; "
            "similarity search will fall back to a sequential scan",
            schema,
            table,
            exc_info=True,
        )


def write_vectors(
    store: PGVectorStore,
    ids: list[str],
    texts: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict],
) -> int:
    """Insert one row per text under *ids*; returns the number written."""
    store.add_embeddings(
        texts=texts, embeddings=embeddings, metadatas=metadatas, ids=ids
    )
    return len(ids)
