"""BM25 indexing: the preprocessing, and a collection made searchable end to end.

The DB test needs ParadeDB (``pg_search``) and skips without it.
"""

import uuid

import psycopg
import pytest

from auto_ontology.infra.postgres import get_postgres_connection_string
from auto_ontology.vdb import bm25_index


def test_preprocess_lowercases_strips_punctuation_and_stopwords() -> None:
    assert bm25_index.preprocess("Daftar Nasabah, yang AKTIF!") == "daftar nasabah aktif"


def test_preprocess_keeps_meaningful_stopwords() -> None:
    # "tidak" and "ada" are Sastrawi stopwords, kept on purpose.
    assert bm25_index.preprocess("Nasabah yang tidak ada transaksi") == (
        "nasabah tidak ada transaksi"
    )


@pytest.fixture
def collection():
    """A collection shaped like the one ``init_vectorstore_table`` creates."""
    name = f"probe_{uuid.uuid4().hex[:8]}"
    try:
        conn = psycopg.connect(get_postgres_connection_string(), connect_timeout=3)
    except Exception as exc:  # noqa: BLE001 -- no database, nothing to assert
        pytest.skip(f"postgres not reachable: {exc}")
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_available_extensions WHERE name = 'pg_search'")
            if cur.fetchone() is None:
                pytest.skip("pg_search not available")
            cur.execute("CREATE SCHEMA IF NOT EXISTS vdb")
            cur.execute(
                f"CREATE TABLE vdb.{name} ("
                "  langchain_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),"
                "  content text NOT NULL,"
                "  database_name varchar(100),"
                "  label varchar(100))"
            )
            # Written before BM25 existed: backfill has to reach it.
            cur.execute(
                f"INSERT INTO vdb.{name} (content, database_name, label) "
                "VALUES ('Term: Nasabah yang aktif', 'db', 'Term')"
            )
        conn.commit()
    try:
        yield name
    finally:
        with psycopg.connect(get_postgres_connection_string()) as cleanup:
            cleanup.execute(f"DROP TABLE IF EXISTS vdb.{name}")


def _search(name: str, query: str) -> list[str]:
    with psycopg.connect(get_postgres_connection_string()) as conn:
        rows = conn.execute(
            f"SELECT content FROM vdb.{name} "
            "WHERE content_cleaned ||| %s AND label = 'Term' ORDER BY content",
            (query,),
        ).fetchall()
    return [row[0] for row in rows]


def test_collection_becomes_searchable(collection) -> None:
    dsn = get_postgres_connection_string()
    bm25_index.ensure_bm25_index(dsn, "vdb", collection)
    # Idempotent: a second writer finds everything in place.
    bm25_index.ensure_bm25_index(dsn, "vdb", collection)

    new_id = str(uuid.uuid4())
    with psycopg.connect(dsn) as conn:
        conn.execute(
            f"INSERT INTO vdb.{collection} (langchain_id, content, database_name, label) "
            "VALUES (%s, 'Term: Rekening tabungan', 'db', 'Term')",
            (new_id,),
        )
    bm25_index.write_bm25(
        dsn, "vdb", collection, [new_id], ["term rekening tabungan"]
    )

    assert _search(collection, "nasabah") == ["Term: Nasabah yang aktif"]
    assert _search(collection, "tabungan") == ["Term: Rekening tabungan"]
